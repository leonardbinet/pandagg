#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from builtins import str as text

from future.utils import iterkeys

from pandagg.interactive.response import IResponse
from pandagg.node.aggs.abstract import UniqueBucketAgg, MetricAgg
from pandagg.tree.response import AggsResponseTree


class Response:
    def __init__(self, data, search):
        self.data = data
        self.__search = search

        self.took = data["took"]
        self.timed_out = data["timed_out"]
        self._shards = data["_shards"]
        self.hits = Hits(data["hits"])
        self.aggregations = Aggregations(
            data.get("aggregations", {}),
            aggs=self.__search._aggs,
            index=self.__search._index,
            query=self.__search._query,
            client=self.__search._using,
        )
        self.profile = data.get("profile")

    @property
    def success(self):
        return (
            self._shards["total"] == self._shards["successful"] and not self.timed_out
        )

    def __len__(self):
        return len(self.hits)

    def __repr__(self):
        return (
            "<Response> took %dms, success: %s, total result %s, contains %s hits"
            % (self.took, self.success, self.hits._total_repr(), len(self.hits))
        )


class Hits:
    def __init__(self, hits):
        self.data = hits
        self.total = hits["total"]
        self.hits = [Hit(hit) for hit in hits.get("hits", [])]
        self.max_score = hits["max_score"]

    def __len__(self):
        return len(self.hits)

    def _total_repr(self):
        if not isinstance(self.total, dict):
            return str(self.total)
        if self.total.get("relation") == "eq":
            return str(self.total["value"])
        if self.total.get("relation") == "gte":
            return ">=%d" % self.total["value"]
        raise ValueError("Invalid total %s" % self.total)

    def __repr__(self):
        if not isinstance(self.total, dict):
            total_repr = text(self.total)
        elif self.total.get("relation") == "eq":
            total_repr = text(self.total["value"])
        elif self.total.get("relation") == "gte":
            total_repr = ">%d" % self.total["value"]
        else:
            raise ValueError("Invalid total %s" % self.total)
        return "<Hits> total: %s, contains %d hits" % (total_repr, len(self.hits))


class Hit:
    def __init__(self, data):
        self.data = data
        self._source = data.get("_source")
        self._score = data.get("_score")
        self._id = data.get("_id")
        self._type = data.get("_type")
        self._index = data.get("_index")

    def __repr__(self):
        return "<Hit %s> score=%.2f" % (self._id, self._score)


class Aggregations:
    def __init__(self, data, aggs, query, index, client):
        self.data = data
        self.__aggs = aggs
        self.__index = index
        self.__query = query
        self.__client = client

    def keys(self):
        return self.data.keys()

    def get(self, key):
        return self.data[key]

    def _parse_group_by(
        self, response, row=None, agg_name=None, until=None, row_as_tuple=False
    ):
        """Recursive parsing of succession of unique child bucket aggregations.

        Yields each row for which last bucket aggregation generated buckets.
        """
        if not row:
            row = [] if row_as_tuple else {}
        agg_name = self.__aggs.root if agg_name is None else agg_name
        if agg_name in response:
            agg_node = self.__aggs.get(agg_name)
            for key, raw_bucket in agg_node.extract_buckets(response[agg_name]):
                child_name = next(
                    (
                        child.name
                        for child in self.__aggs.children(agg_name, id_only=False)
                    ),
                    None,
                )
                sub_row = row.copy()
                # aggs generating a single bucket don't require to be listed in grouping keys
                if not isinstance(agg_node, UniqueBucketAgg):
                    if row_as_tuple:
                        sub_row.append(key)
                    else:
                        sub_row[agg_name] = key
                if child_name and agg_name != until:
                    # yield children
                    for sub_row, sub_raw_bucket in self._parse_group_by(
                        row=sub_row,
                        response=raw_bucket,
                        agg_name=child_name,
                        until=until,
                        row_as_tuple=row_as_tuple,
                    ):
                        yield sub_row, sub_raw_bucket
                else:
                    # end real yield
                    if row_as_tuple:
                        sub_row = tuple(sub_row)
                    yield sub_row, raw_bucket

    def _normalize_buckets(self, agg_response, agg_name=None):
        """Recursive function to parse aggregation response as a normalized entities.
        Each response bucket is represented as a dict with keys (key, level, value, children)::

            {
                "level": "owner.id",
                "key": 35,
                "value": 235,
                "children": [
                ]
            }
        """
        agg_name = agg_name or self.__aggs.root
        agg_node = self.__aggs.get(agg_name)
        agg_children = self.__aggs.children(agg_node.name, id_only=False)
        for key, raw_bucket in agg_node.extract_buckets(agg_response[agg_name]):
            result = {
                "level": agg_name,
                "key": key,
                "value": agg_node.extract_bucket_value(raw_bucket),
            }
            normalized_children = [
                normalized_child
                for child in agg_children
                for normalized_child in self._normalize_buckets(
                    agg_name=child.name, agg_response=raw_bucket
                )
            ]
            if normalized_children:
                result["children"] = normalized_children
            yield result

    def _grouping_agg(self, name=None):
        """return agg node or None"""
        name = self.__aggs.deepest_linear_bucket_agg if name is None else name
        if name is None:
            return None
        if name not in self.__aggs:
            raise ValueError("Cannot group by <%s>, agg node does not exist" % name)
        return self.__aggs.get(name)

    def serialize_as_tabular(
        self, row_as_tuple=False, grouped_by=None, normalize_children=True,
    ):
        """Build tabular view of ES response grouping levels (rows) until 'grouped_by' aggregation node included is
        reached, and using children aggregations of grouping level as values for each of generated groups (columns).

        Suppose an aggregation of this shape (A & B bucket aggregations)::

            A──> B──> C1
                 ├──> C2
                 └──> C3

        With grouped_by='B', breakdown ElasticSearch response (tree structure), into a tabular structure of this shape::

                                  C1     C2    C3
            A           B
            wood        blue      10     4     0
                        red       7      5     2
            steel       blue      1      9     0
                        red       23     4     2

        :param row_as_tuple: if True, level-key samples are returned as tuples, else in a dictionnary
        :param grouped_by: name of the aggregation node used as last grouping level
        :param normalize_children: if True, normalize columns buckets
        :return: index, index_names, values
        """
        grouped_by = (
            self.__aggs.deepest_linear_bucket_agg if grouped_by is None else grouped_by
        )
        if grouped_by is not None:
            if grouped_by not in self.__aggs:
                raise ValueError(
                    "Cannot group by <%s>, agg node does not exist" % grouped_by
                )
            index_values = list(
                self._parse_group_by(
                    response=self.data, row_as_tuple=row_as_tuple, until=grouped_by
                )
            )
        elif row_as_tuple:
            index_values = [((None,), self.data)]
        else:
            index_values = [({}, self.data)]

        if not index_values:
            return [], [], []
        index, values = zip(*index_values)

        grouping_agg = self.__aggs.get(grouped_by)
        grouping_agg_children = self.__aggs.children(grouped_by, id_only=False)

        index_names = [
            a.name
            for a in self.__aggs.ancestors(
                grouping_agg.name, id_only=False, from_root=True
            )
            + [grouping_agg]
            if not isinstance(a, UniqueBucketAgg)
        ]

        def serialize_columns(row_data, gr_agg=None):
            # extract value (usually 'doc_count') of grouping agg node
            result = {}
            if gr_agg:
                result[gr_agg.VALUE_ATTRS[0]] = gr_agg.extract_bucket_value(row_data)

            if not grouping_agg_children:
                return result
            # extract values of children, one columns per child
            for child in grouping_agg_children:
                if not normalize_children:
                    result[child.name] = row_data[child.name]
                    continue
                if isinstance(child, (UniqueBucketAgg, MetricAgg)):
                    result[child.name] = child.extract_bucket_value(
                        row_data[child.name]
                    )
                else:
                    result[child.name] = next(
                        self._normalize_buckets(row_data, child.name), None
                    )
            return result

        serialized_values = list(
            map(lambda v: serialize_columns(v, gr_agg=grouping_agg), values)
        )
        return index, index_names, serialized_values

    def serialize_as_dataframe(self, grouped_by=None, normalize_children=True):
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                'Using dataframe output format requires to install pandas. Please install "pandas" or '
                "use another output format."
            )
        index, index_names, values = self.serialize_as_tabular(
            row_as_tuple=True,
            grouped_by=grouped_by,
            normalize_children=normalize_children,
        )
        if not index:
            return pd.DataFrame()
        if len(index[0]) == 0:
            index = (None,) * len(index)
        else:
            index = pd.MultiIndex.from_tuples(index, names=index_names)
        return pd.DataFrame(index=index, data=values)

    def serialize_as_normalized(self):
        children = []
        for k in sorted(iterkeys(self.data)):
            for child in self._normalize_buckets(self.data, k):
                children.append(child)
        return {"level": "root", "key": None, "value": None, "children": children}

    def serialize_as_tree(self):
        return AggsResponseTree(data=self.data, aggs=self.__aggs, index=self.__index)

    def serialize_as_interactive_tree(self):
        return IResponse(
            tree=self.serialize_as_tree(),
            index_name=self.__index,
            query=self.__query,
            client=self.__client,
            depth=1,
        )

    def serialize(self, output="dataframe", **kwargs):
        """
        :param output: output format, one of "raw", "tree", "normalized_tree", "dict_rows", "dataframe"
        :param kwargs: serialization kwargs
        :return:
        """
        if output == "raw":
            return self.data
        elif output == "tree":
            return self.serialize_as_tree()
        elif output == "interactive_tree":
            return self.serialize_as_interactive_tree()
        elif output == "normalized_tree":
            return self.serialize_as_normalized()
        elif output == "dict_rows":
            return self.serialize_as_tabular(**kwargs)
        elif output == "dataframe":
            return self.serialize_as_dataframe(**kwargs)
        else:
            raise NotImplementedError("Unkown %s output format." % output)

    def __repr__(self):
        if not self.keys():
            return "<Aggregations> empty"
        return "<Aggregations> %s" % list(map(text, self.keys()))