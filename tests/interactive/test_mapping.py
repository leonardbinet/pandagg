#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mock import Mock
from unittest import TestCase

from pandagg.node.mapping.abstract import Field
from pandagg.node.mapping.field_datatypes import Keyword, Text, Nested, Object, Integer
from pandagg.tree.mapping import Mapping
from pandagg.interactive._field_agg_factory import field_classes_per_name
from pandagg.interactive.mapping import IMapping

from tests.testing_samples.mapping_example import MAPPING


class IMappingTestCase(TestCase):
    def test_mapping_aggregations(self):
        mapping_tree = Mapping(MAPPING)
        # check that leaves are expanded, based on 'field_name' attribute of nodes
        mapping = IMapping(mapping_tree, depth=1)
        for field_name in (
            "classification_type",
            "date",
            "global_metrics",
            "id",
            "language",
            "local_metrics",
            "workflow",
        ):
            self.assertTrue(hasattr(mapping, field_name))

        workflow = mapping.workflow
        # Check that calling a tree will return its root node.
        workflow_node = workflow()
        self.assertTrue(isinstance(workflow_node, Field))

    def test_imapping_init(self):

        mapping_dict = {
            "dynamic": False,
            "properties": {
                "classification_type": {
                    "type": "keyword",
                    "fields": {"raw": {"type": "text"}},
                },
                "local_metrics": {
                    "type": "nested",
                    "dynamic": False,
                    "properties": {
                        "dataset": {
                            "dynamic": False,
                            "properties": {
                                "support_test": {"type": "integer"},
                                "support_train": {"type": "integer"},
                            },
                        }
                    },
                },
            },
        }

        mapping_tree = Mapping(mapping_dict)
        client_mock = Mock(spec=["search"])
        index_name = "classification_report_index_name"

        # from dict
        im1 = IMapping(mapping_dict, client=client_mock, index=index_name)
        # from tree
        im2 = IMapping(mapping_tree, client=client_mock, index=index_name)

        # from nodes
        im3 = IMapping(
            properties={
                Keyword("classification_type", fields=[Text("raw")]),
                Nested(
                    "local_metrics",
                    dynamic=False,
                    properties=[
                        Object(
                            "dataset",
                            dynamic=False,
                            properties=[
                                Integer("support_test"),
                                Integer("support_train"),
                            ],
                        )
                    ],
                ),
            },
            dynamic=False,
            client=client_mock,
            index=index_name,
        )
        for i, m in enumerate((im1, im2, im3)):
            self.assertEqual(
                m._tree.serialize(), mapping_dict, "failed at m%d" % (i + 1)
            )
            self.assertEqual(m._index, index_name)
            self.assertIs(m._client, client_mock)

    def test_client_bound(self):
        """Check that when reaching leaves (fields without children) leaves have the "a" attribute that can generate
        aggregations on that field type.
        """
        client_mock = Mock(spec=["search"])
        es_response_mock = {
            "_shards": {"failed": 0, "successful": 135, "total": 135},
            "aggregations": {
                "terms_agg": {
                    "buckets": [
                        {"doc_count": 25, "key": 1},
                        {"doc_count": 50, "key": 2},
                    ],
                    "doc_count_error_upper_bound": 0,
                    "sum_other_doc_count": 4,
                }
            },
            "hits": {"hits": [], "max_score": 0.0, "total": 300},
            "timed_out": False,
            "took": 30,
        }
        client_mock.search = Mock(return_value=es_response_mock)

        mapping_tree = Mapping(MAPPING)
        client_bound_mapping = IMapping(
            mapping_tree, client=client_mock, index="classification_report_index_name",
        )

        workflow_field = client_bound_mapping.workflow
        self.assertTrue(hasattr(workflow_field, "a"))
        # workflow type is String
        self.assertIsInstance(workflow_field.a, field_classes_per_name["keyword"])

        response = workflow_field.a.terms(
            size=20,
            raw_output=True,
            query={"term": {"classification_type": "multiclass"}},
        )
        self.assertEqual(
            response,
            [(1, {"doc_count": 25, "key": 1}), (2, {"doc_count": 50, "key": 2}),],
        )
        client_mock.search.assert_called_once()
        client_mock.search.assert_called_with(
            body={
                "aggs": {"terms_agg": {"terms": {"field": "workflow", "size": 20}}},
                "size": 0,
                "query": {"term": {"classification_type": "multiclass"}},
            },
            index="classification_report_index_name",
        )
