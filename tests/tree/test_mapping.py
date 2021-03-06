#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase

from mock import patch

from pandagg.exceptions import AbsentMappingFieldError
from pandagg.node.mapping.abstract import Field
from pandagg.node.mapping.field_datatypes import Keyword, Object, Text, Nested, Integer
from pandagg.tree.mapping import Mapping
from tests.testing_samples.mapping_example import MAPPING, EXPECTED_MAPPING_TREE_REPR


class MappingTreeTestCase(TestCase):
    """All tree logic is tested in utils.
    Here, check that:
     - a dict mapping is correctly parsed into a tree,
     - it has the right representation.
    """

    def test_node_repr(self):
        node = Keyword(name="path.to.field", fields={"searchable": {"type": "text"}})
        self.assertEqual(
            node.__str__(),
            u"""<Mapping Field path.to.field> of type keyword:
{
    "type": "keyword"
}""",
        )

    def test_deserialization(self):
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

        m1 = Mapping(mapping_dict)

        m2 = Mapping(
            dynamic=False,
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
        )

        expected_repr = """<Mapping>
_                                                              
├── classification_type                                       Keyword
│   └── raw                                                 ~ Text
└── local_metrics                                            [Nested]
    └── dataset                                              {Object}
        ├── support_test                                      Integer
        └── support_train                                     Integer
"""
        for i, m in enumerate((m1, m2,)):
            self.assertEqual(m.__repr__(), expected_repr, "failed at m%d" % (i + 1))
            self.assertEqual(m.serialize(), mapping_dict, "failed at m%d" % (i + 1))

    def test_parse_tree_from_dict(self):
        mapping_tree = Mapping(MAPPING)

        self.assertEqual(mapping_tree.__str__(), EXPECTED_MAPPING_TREE_REPR)

    def test_nesteds_applied_at_field(self):
        mapping_tree = Mapping(MAPPING)

        self.assertEqual(mapping_tree.nested_at_field("classification_type"), None)
        self.assertEqual(mapping_tree.list_nesteds_at_field("classification_type"), [])
        self.assertEqual(mapping_tree.nested_at_field("date"), None)
        self.assertEqual(mapping_tree.list_nesteds_at_field("date"), [])
        self.assertEqual(mapping_tree.nested_at_field("global_metrics"), None)
        self.assertEqual(mapping_tree.list_nesteds_at_field("global_metrics"), [])

        self.assertEqual(mapping_tree.nested_at_field("local_metrics"), "local_metrics")
        self.assertEqual(
            mapping_tree.list_nesteds_at_field("local_metrics"), ["local_metrics"]
        )
        self.assertEqual(
            mapping_tree.nested_at_field("local_metrics.dataset.support_test"),
            "local_metrics",
        )
        self.assertEqual(
            mapping_tree.list_nesteds_at_field("local_metrics.dataset.support_test"),
            ["local_metrics"],
        )

    @patch("uuid.uuid4")
    def test_resolve_path_to_id(self, uuid_mock):
        uuid_mock.side_effect = range(100)
        mapping_tree = Mapping(MAPPING)
        # do not resolve
        self.assertEqual(
            mapping_tree.resolve_path_to_id("global_metrics.non_existing_field"),
            "global_metrics.non_existing_field",
        )
        # resolve
        self.assertEqual(
            mapping_tree.resolve_path_to_id("classification_type"),
            "classification_type0",
        )
        self.assertEqual(
            mapping_tree.resolve_path_to_id("local_metrics.dataset.support_test"),
            "support_test23",
        )

    def test_mapping_type_of_field(self):
        mapping_tree = Mapping(MAPPING)
        with self.assertRaises(AbsentMappingFieldError):
            self.assertEqual(mapping_tree.mapping_type_of_field("yolo"), False)

        self.assertEqual(mapping_tree.mapping_type_of_field("global_metrics"), "object")
        self.assertEqual(mapping_tree.mapping_type_of_field("local_metrics"), "nested")
        self.assertEqual(
            mapping_tree.mapping_type_of_field("global_metrics.field.name.raw"),
            "keyword",
        )
        self.assertEqual(
            mapping_tree.mapping_type_of_field("local_metrics.dataset.support_test"),
            "integer",
        )

    def test_node_path(self):
        mapping_tree = Mapping(MAPPING)
        # get node by path syntax
        node = mapping_tree.get("local_metrics.dataset.support_test")
        self.assertIsInstance(node, Field)
        self.assertEqual(node.name, "support_test")
        self.assertEqual(
            mapping_tree.node_path(node.identifier),
            "local_metrics.dataset.support_test",
        )
