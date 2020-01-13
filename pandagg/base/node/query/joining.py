from pandagg.base.node.query import CompoundClause
from pandagg.base.node.query._parameter_clause import Path, QueryP


class Nested(CompoundClause):
    DEFAULT_OPERATOR = QueryP
    PARAMS_WHITELIST = ['path', 'query', 'score_mode', 'ignore_unmapped']
    KEY = 'nested'

    def __init__(self, *args, **kwargs):
        super(Nested, self).__init__(*args, **kwargs)
        self.path = next((c.body['value'] for c in self.children if isinstance(c, Path)))


class HasChild(CompoundClause):
    KEY = 'has_child'


class HasParent(CompoundClause):
    KEY = 'has_parent'


class ParentId(CompoundClause):
    KEY = 'parent_id'


JOINING_QUERIES = [
    Nested,
    HasChild,
    HasParent,
    ParentId
]
