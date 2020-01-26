#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from pandagg.base.node.types import NUMERIC_TYPES
from pandagg.base.node.agg.abstract import FieldMetricAgg, MetricAgg


class TopHits(MetricAgg):
    # TODO - test this one
    VALUE_ATTRS = ['hits']
    AGG_TYPE = 'top_hits'


class Avg(FieldMetricAgg):
    WHITELISTED_MAPPING_TYPES = NUMERIC_TYPES
    VALUE_ATTRS = ['value']
    AGG_TYPE = 'avg'


class Max(FieldMetricAgg):
    WHITELISTED_MAPPING_TYPES = NUMERIC_TYPES
    VALUE_ATTRS = ['value']
    AGG_TYPE = 'max'


class Min(FieldMetricAgg):
    WHITELISTED_MAPPING_TYPES = NUMERIC_TYPES
    VALUE_ATTRS = ['value']
    AGG_TYPE = 'min'


class Cardinality(FieldMetricAgg):
    VALUE_ATTRS = ['value']
    AGG_TYPE = 'cardinality'


class Stats(FieldMetricAgg):
    WHITELISTED_MAPPING_TYPES = NUMERIC_TYPES
    VALUE_ATTRS = ['count', 'min', 'max', 'avg', 'sum']
    AGG_TYPE = 'stats'


class ExtendedStats(FieldMetricAgg):
    WHITELISTED_MAPPING_TYPES = NUMERIC_TYPES
    VALUE_ATTRS = [
        'count', 'min', 'max', 'avg', 'sum', 'sum_of_squares', 'variance', 'std_deviation', 'std_deviation_bounds']
    AGG_TYPE = 'extended_stats'


class GeoBound(FieldMetricAgg):
    WHITELISTED_MAPPING_TYPES = ['geo_point']
    VALUE_ATTRS = ['bounds']
    AGG_TYPE = 'geo_bounds'


class GeoCentroid(FieldMetricAgg):
    WHITELISTED_MAPPING_TYPES = ['geo_point']
    VALUE_ATTRS = ['location']
    AGG_TYPE = 'geo_centroid'


class Percentiles(FieldMetricAgg):
    """Percents body argument can be passed to specify which percentiles to fetch."""
    WHITELISTED_MAPPING_TYPES = NUMERIC_TYPES
    VALUE_ATTRS = ['values']
    AGG_TYPE = 'percentiles'


class PercentileRanks(FieldMetricAgg):
    WHITELISTED_MAPPING_TYPES = NUMERIC_TYPES
    VALUE_ATTRS = ['values']
    AGG_TYPE = 'percentile_ranks'

    def __init__(self, name, field, values, meta=None, **body):
        super(PercentileRanks, self).__init__(name=name, field=field, meta=meta, values=values, **body)


class ValueCount(FieldMetricAgg):
    BLACKLISTED_MAPPING_TYPES = []
    VALUE_ATTRS = ['value']
    AGG_TYPE = 'value_count'


METRIC_AGGS = [
    Avg,
    Max,
    Min,
    Cardinality,
    Stats,
    ExtendedStats,
    Percentiles,
    PercentileRanks,
    GeoBound,
    GeoCentroid,
    TopHits,
    ValueCount
]
