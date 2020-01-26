#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Not implemented aggregations include:
- children agg
- geo-distance
- geo-hash grid
- ipv4
- sampler
- significant terms
"""

from builtins import str as text

from operator import itemgetter
from six import iteritems

from pandagg.base.utils import bool_if_required
from pandagg.base.node.types import NUMERIC_TYPES
from pandagg.base.node.agg.abstract import ListBucketAgg, UniqueBucketAgg, BucketAggNode


class Global(UniqueBucketAgg):

    AGG_TYPE = 'global'
    VALUE_ATTRS = ['doc_count']

    def __init__(self, name, meta=None, aggs=None):
        super(Global, self).__init__(
            name=name,
            agg_body={},
            meta=meta,
            aggs=aggs
        )

    def get_filter(self, key):
        return None


class Filter(UniqueBucketAgg):

    AGG_TYPE = 'filter'
    VALUE_ATTRS = ['doc_count']

    def __init__(self, name, filter, meta=None, aggs=None, **body):
        self.filter = filter
        super(Filter, self).__init__(
            name=name,
            meta=meta,
            aggs=aggs,
            filter=filter,
            **body
        )

    def get_filter(self, key):
        return self.filter


class MatchAll(Filter):

    def __init__(self, name, meta=None, aggs=None):
        super(MatchAll, self).__init__(
            name=name,
            filter={'match_all': {}},
            meta=meta,
            aggs=aggs
        )


class Nested(UniqueBucketAgg):

    AGG_TYPE = 'nested'
    VALUE_ATTRS = ['doc_count']
    WHITELISTED_MAPPING_TYPES = ['nested']

    def __init__(self, name, path, meta=None, aggs=None):
        self.path = path
        super(Nested, self).__init__(
            name=name,
            path=path,
            meta=meta,
            aggs=aggs
        )

    def get_filter(self, key):
        return None


class ReverseNested(UniqueBucketAgg):

    AGG_TYPE = 'reverse_nested'
    VALUE_ATTRS = ['doc_count']
    WHITELISTED_MAPPING_TYPES = ['nested']

    def __init__(self, name, path=None, meta=None, aggs=None, **body):
        self.path = path
        body_kwargs = dict(body)
        if path:
            body_kwargs['path'] = path
        super(ReverseNested, self).__init__(
            name=name,
            meta=meta,
            aggs=aggs,
            **body_kwargs
        )

    def get_filter(self, key):
        return None


class Missing(UniqueBucketAgg):
    AGG_TYPE = 'missing'
    VALUE_ATTRS = ['doc_count']
    BLACKLISTED_MAPPING_TYPES = []

    def __init__(self, name, field, meta=None, aggs=None, **body):
        super(UniqueBucketAgg, self).__init__(
            name=name,
            field=field,
            meta=meta,
            aggs=aggs,
            **body
        )

    def get_filter(self, key):
        return {'bool': {'must_not': {'exists': {'field': self.field}}}}


class Terms(ListBucketAgg):
    """Terms aggregation.
    """
    AGG_TYPE = 'terms'
    VALUE_ATTRS = ['doc_count', 'doc_count_error_upper_bound', 'sum_other_doc_count']
    BLACKLISTED_MAPPING_TYPES = []

    def __init__(self, name, field, missing=None, size=None, aggs=None, meta=None, **body):
        self.field = field
        self.missing = missing
        self.size = size

        body_kwargs = dict(body)
        if missing is not None:
            body_kwargs["missing"] = missing
        if size is not None:
            body_kwargs["size"] = size

        super(Terms, self).__init__(
            name=name,
            field=field,
            meta=meta,
            aggs=aggs,
            **body_kwargs
        )

    def get_filter(self, key):
        """Provide filter to get documents belonging to document of given key."""
        if key == 'missing':
            return {'bool': {'must_not': {'exists': {'field': self.field}}}}
        return {'term': {self.field: key}}


class Filters(BucketAggNode):

    AGG_TYPE = 'filters'
    VALUE_ATTRS = ['doc_count']
    DEFAULT_OTHER_KEY = '_other_'

    def __init__(self, name, filters, other_bucket=False, other_bucket_key=None, meta=None, aggs=None, **body):
        self.filters = filters
        self.other_bucket = other_bucket
        self.other_bucket_key = other_bucket_key
        body_kwargs = dict(body)
        if other_bucket:
            body_kwargs['other_bucket'] = other_bucket
        if other_bucket_key:
            body_kwargs['other_bucket_key'] = other_bucket_key

        super(Filters, self).__init__(
            name=name,
            filters=filters,
            meta=meta,
            aggs=aggs,
            **body_kwargs
        )

    def extract_buckets(self, response_value):
        buckets = response_value['buckets']
        for key in sorted(buckets.keys()):
            yield (key, buckets[key])

    def get_filter(self, key):
        """Provide filter to get documents belonging to document of given key."""
        if key in self.filters.keys():
            return self.filters[key]
        if self.other_bucket:
            if key == self.DEFAULT_OTHER_KEY or key == self.other_bucket_key:
                # necessary sort for python2/python3 identical output order in tests
                key_filter_tuples = [(k, filter_) for k, filter_ in iteritems(self.filters)]
                return {'bool': {
                    'must_not': bool_if_required(
                        list(map(itemgetter(1), sorted(key_filter_tuples, key=itemgetter(0)))),
                        operator='should'
                    )}
                }
        raise ValueError('Unkown <%s> key in <Agg %s>' % (key, self.name))


class Histogram(ListBucketAgg):

    AGG_TYPE = 'histogram'
    VALUE_ATTRS = ['doc_count']
    WHITELISTED_MAPPING_TYPES = NUMERIC_TYPES

    def __init__(self, name, field, interval, format_=None, meta=None, aggs=None, **body):
        self.field = field
        self.interval = interval
        self.hist_format = format_
        body_kwargs = dict(body)
        if format_:
            body_kwargs['format'] = format_
        super(Histogram, self).__init__(
            name=name,
            field=field,
            interval=interval,
            meta=meta,
            aggs=aggs,
            **body_kwargs
        )

    def get_filter(self, key):
        # TODO
        return None

    @classmethod
    def deserialize(cls, name, **params):
        # avoid modifying inplace
        params = params.copy()
        # special case for format_ keyword, we don't want to shadow `format` keyword
        if 'format' in params:
            params['format_'] = params.pop('format')
        return cls(name=name, **params)


class DateHistogram(Histogram):
    AGG_TYPE = 'date_histogram'
    VALUE_ATTRS = ['doc_count']
    WHITELISTED_MAPPING_TYPES = ['date']

    def __init__(self, name, field, interval=None, calendar_interval=None, fixed_interval=None, meta=None,
                 key_as_string=True, aggs=None, **body):
        # interval is deprecated from 7.2 in favor of calendar_interval and fixed interval
        if not(interval or fixed_interval or calendar_interval):
            raise ValueError('One of "interval", "calendar_interval" or "fixed_interval" must be provided.')
        if interval:
            body['interval'] = interval
        if calendar_interval:
            body['calendar_interval'] = calendar_interval
        if fixed_interval:
            body['fixed_interval'] = fixed_interval
        if key_as_string:
            self.KEY_PATH = 'key_as_string'
        super(DateHistogram, self).__init__(
            name=name,
            field=field,
            meta=meta,
            aggs=aggs,
            **body
        )


class Range(BucketAggNode):
    AGG_TYPE = 'range'
    VALUE_ATTRS = ['doc_count']
    WHITELISTED_MAPPING_TYPES = NUMERIC_TYPES
    SINGLE_BUCKET = False
    KEY_SEP = '-'

    def __init__(self, name, field, ranges, keyed=False, meta=None, aggs=None, **body):
        self.field = field
        self.ranges = ranges
        self.keyed = keyed
        body_kwargs = dict(body)
        if keyed:
            self.KEY_SUFFIX = '_as_string'
            body_kwargs['keyed'] = keyed
        else:
            self.KEY_SUFFIX = None
        super(Range, self).__init__(
            name=name,
            field=field,
            ranges=ranges,
            meta=meta,
            aggs=aggs,
            **body_kwargs
        )

    @property
    def from_key(self):
        if self.KEY_SUFFIX:
            return 'from%s' % self.KEY_SUFFIX
        return 'from'

    @property
    def to_key(self):
        if self.KEY_SUFFIX:
            return 'to%s' % self.KEY_SUFFIX
        return 'to'

    def extract_buckets(self, response_value):
        if self.keyed:
            buckets = response_value['buckets']
            for key in sorted(buckets.keys()):
                yield (key, buckets[key])
        else:
            for bucket in response_value['buckets']:
                if self.from_key in bucket:
                    key = '%s%s' % (bucket[self.from_key], self.KEY_SEP)
                else:
                    key = '*-'
                if self.to_key in bucket:
                    key += text(bucket[self.to_key])
                else:
                    key += '*'
                yield key, bucket

    def get_filter(self, key):
        from_, to_ = key.split(self.KEY_SEP)
        inner = {}
        if from_ != '*':
            inner['gte'] = from_
        if to_ != '*':
            inner['lt'] = to_
        return {'range': {self.field: inner}}


class DateRange(Range):
    AGG_TYPE = 'date_range'
    VALUE_ATTRS = ['doc_count']
    WHITELISTED_MAPPING_TYPES = ['date']
    SINGLE_BUCKET = False
    # cannot use range '-' separator since some keys contain it
    KEY_SEP = '::'

    def __init__(self, name, field, key_as_string=True, aggs=None, meta=None, **body):
        self.key_as_string = key_as_string
        super(DateRange, self).__init__(
            name=name,
            field=field,
            keyed=True,
            meta=meta,
            aggs=aggs,
            **body
        )


BUCKET_AGGS = [
    Terms,
    Filters,
    Histogram,
    DateHistogram,
    Global,
    Filter,
    Nested,
    ReverseNested,
    Range,
    DateRange,
    Missing
]
