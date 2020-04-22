#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lighttree import TreeBasedObj
from pandagg.interactive._field_agg_factory import field_classes_per_name
from pandagg.tree.mapping import Mapping


def as_mapping(mapping):
    if isinstance(mapping, Mapping):
        return mapping
    elif isinstance(mapping, IMapping):
        return mapping._tree
    elif isinstance(mapping, dict):
        return Mapping(mapping)
    else:
        raise NotImplementedError()


class IMapping(TreeBasedObj):
    """Interactive wrapper upon mapping tree.
    """

    _NODE_PATH_ATTR = "name"

    def __init__(self, *args, **kwargs):
        self._client = kwargs.pop("client", None)
        self._index_name = kwargs.pop("index_name", None)
        root_path = kwargs.pop("root_path", None)
        depth = kwargs.pop("depth", 1)
        initial_tree = kwargs.pop("initial_tree", None)
        tree = Mapping(*args, **kwargs)
        super(IMapping, self).__init__(
            tree=tree, root_path=root_path, depth=depth, initial_tree=initial_tree
        )
        # if we reached a leave, add aggregation capabilities based on reached mapping type
        self._set_agg_property_if_required()

    def _bind(self, client, index_name=None):
        self._client = client
        if index_name is not None:
            self._index_name = index_name
        self._set_agg_property_if_required()
        return self

    def _clone(self, nid, root_path, depth):
        return IMapping(
            self._tree.subtree(nid),
            client=self._client,
            root_path=root_path,
            depth=depth,
            initial_tree=self._initial_tree,
            index_name=self._index_name,
        )

    def _set_agg_property_if_required(self):
        if self._client is not None and not self._tree.children(self._tree.root):
            field_node = self._tree.get(self._tree.root)
            if field_node.KEY in field_classes_per_name:
                self.a = field_classes_per_name[field_node.KEY](
                    mapping_tree=self._initial_tree,
                    client=self._client,
                    field=self._initial_tree.node_path(field_node.identifier),
                    index_name=self._index_name,
                )

    def __call__(self, *args, **kwargs):
        return self._tree.get(self._tree.root)
