#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pandagg.tree import Tree, Node
from collections import OrderedDict

from treelib.exceptions import NodeIDAbsentError


class PrettyNode:
    # class to display pretty nodes while working with trees
    def __init__(self, pretty):
        self.pretty = pretty


class ResponseNode(Node):

    REPR_SIZE = 60

    def __init__(self, aggregation_node, value, lvl, key=None, override_current_level=None):
        self.aggregation_node = aggregation_node
        self.value = value
        self.lvl = lvl
        # `override_current_level` is only used to create root node of response tree
        self.current_level = override_current_level or aggregation_node.agg_name
        self.current_key = key
        pretty = self._str_current_level(
            level=self.current_level,
            key=self.current_key,
            lvl=self.lvl, sep='=',
            value=self.extract_bucket_value()
        )
        super(ResponseNode, self).__init__(data=PrettyNode(pretty=pretty))

    @classmethod
    def _str_current_level(cls, level, key, lvl, sep=':', value=None):
        s = level
        if key is not None:
            s = '%s%s%s' % (s, sep, key)
        if value is not None:
            pad = max(cls.REPR_SIZE - 4 * lvl - len(s) - len(str(value)), 4)
            s = s + ' ' * pad + str(value)
        return s

    def extract_bucket_value(self, value_as_dict=False):
        attrs = self.aggregation_node.VALUE_ATTRS
        if value_as_dict:
            return {attr_: self.value.get(attr_) for attr_ in attrs}
        return self.value.get(attrs[0])

    def __repr__(self):
        return u'<Bucket, {pretty}, identifier={identifier}>'.format(identifier=self.identifier, pretty=self.data.pretty).encode('utf-8')


class AggregationResponse(Tree):

    def __init__(self, agg_tree):
        super(AggregationResponse, self).__init__()
        self.agg_tree = agg_tree

    def subtree(self, nid):
        st = AggregationResponse(agg_tree=self.agg_tree)
        if nid is None:
            return st

        if not self.contains(nid):
            raise NodeIDAbsentError("Node '%s' is not in the tree" % nid)

        st.root = nid
        for node_n in self.expand_tree(nid):
            st._nodes.update({self[node_n].identifier: self[node_n]})
        return st

    def parse_aggregation(self, raw_response):
        # init tree with fist node called 'aggs'
        agg_node = self.agg_tree[self.agg_tree.root]
        response_node = ResponseNode(
            aggregation_node=agg_node,
            value=raw_response,
            override_current_level='aggs',
            lvl=0
        )
        self.add_node(response_node)
        self._parse_node_with_children(agg_node, response_node)
        return self

    def _parse_node_with_children(self, agg_node, parent_node, lvl=1):
        agg_value = parent_node.value.get(agg_node.agg_name)
        if agg_value:
            # if no data is present, elasticsearch doesn't return any bucket, for instance for TermAggregations
            for key, value in agg_node.extract_buckets(agg_value):
                bucket = ResponseNode(aggregation_node=agg_node, key=key, value=value, lvl=lvl+1)
                self.add_node(bucket, parent_node.identifier)
                for child in self.agg_tree.children(agg_node.agg_name):
                    self._parse_node_with_children(agg_node=child, parent_node=bucket, lvl=lvl+1)

    def list_buckets(self, nid=None, current_level=None):
        if nid is not None:
            return self.subtree(nid).list_buckets(nid=None, current_level=current_level)
        buckets = self.nodes.values()
        if current_level is not None:
            buckets = [bucket for bucket in buckets if bucket.current_level == current_level]
        return buckets

    def bucket_level_key(self, bucket, level, exc=False):
        if bucket.current_level == level:
            return bucket.current_key
        parent = self.parent(bucket.identifier)
        if parent:
            return self.bucket_level_key(parent, level, exc)
        if exc:
            raise ValueError('Level not found %s' % level)

    def bucket_id_dict(self, bucket, id_dict=None, end_level=None, depth=None):
        if id_dict is None:
            id_dict = OrderedDict()
        id_dict[bucket.current_level] = bucket.current_key
        if depth is not None:
            depth -= 1
        parent = self.parent(bucket.identifier)
        if bucket.current_level == end_level or depth == 0 or parent is None:
            return id_dict
        return self.bucket_id_dict(parent, id_dict, end_level, depth)

    def show(self, data_property='pretty', **kwargs):
        super(AggregationResponse, self).show(data_property=data_property)

    def __repr__(self):
        self.show()
        return (u'<{class_}>\n{tree}'.format(class_=self.__class__.__name__, tree=self._reader)).encode('utf-8')