## What is it?

**pandagg** is a Python package providing a simple interface to manipulate ElasticSearch queries and aggregations.

***Disclaimer*** *:this is a pre-release version*
## Features

- flexible aggregation and search queries declaration
- query validation based on provided mapping
- parsing of aggregation results in handy formats: tree with interactive navigation, csv-like tabular breakdown, and others
- mapping interactive navigation


## Usage

### Documentation
Full documentation and user-guide are available [here on read-the-docs](https://pandagg.readthedocs.io/en/latest/).

### Quick sneak peek 
**Elasticsearch dict syntax**
```
>>> from pandagg.query import Query

>>> expected_query = {'bool': {'must': [
    {'terms': {'genres': ['Action', 'Thriller']}},
    {'range': {'rank': {'gte': 7}}},
    {'nested': {
        'path': 'roles',
        'query': {'bool': {'must': [
            {'term': {'roles.gender': {'value': 'F'}}},
            {'term': {'roles.role': {'value': 'Reporter'}}}]}
         }
    }}
]}}
>>> q = Query(expected_query)
>>> q
<Query>
bool
└── must
    ├── nested
    │   ├── path="roles"
    │   └── query
    │       └── bool
    │           └── must
    │               ├── term, field=roles.gender, value="F"
    │               └── term, field=roles.role, value="Reporter"
    ├── range, field=rank, gte=7
    └── terms, field=genres, values=['Action', 'Thriller']
```

**DSL syntax**
```
from pandagg.query import Nested, Bool, Query, Range, Term, Terms
>>> q = Query(
    Bool(must=[
        TermsFilter('genres', terms=['Action', 'Thriller']),
        Range('rank', gte=7),
        Nested(
            path='roles', 
            query=Bool(must=[
                Term('roles.gender', value='F'),
                Term('roles.role', value='Reporter')
            ])
        )
    ])
)

# serialized query is computed by `query_dict` method
>>> q.query_dict() == expected_query
True
```

**Chained syntax**

```
>>> from pandagg.query import Query, Range, Term

>>> q = Query()\
    .query({'terms': {'genres': ['Action', 'Thriller']}})\
    .nested(path='roles', _name='nested_roles', query=Term('roles.gender', value='F'))\
    .query(Range('rank', gte=7))\
    .query(Term('roles.role', value='Reporter'), parent='nested_roles')

>>> q
<Query>
bool
└── must
    ├── nested
    │   ├── path="roles"
    │   └── query
    │       └── bool
    │           └── must
    │               ├── term, field=roles.gender, value="F"
    │               └── term, field=roles.role, value="Reporter"
    ├── range, field=rank, gte=7
    └── terms, field=genres, values=['Action', 'Thriller']
     
```
Notes:
 - both DSL and dict syntaxes are accepted in `Query` compound clauses methods (`query`, `nested`, `must` etc).
 - the last query uses the nested clause `_name` to detect where it should be inserted

## Installation
```
pip install pandagg
```

## Dependencies
**Hard dependency**: [ligthtree](https://pypi.org/project/lighttree/): 0.0.2 or higher

**Soft dependency**: to parse aggregation results as tabular dataframe: [pandas](https://github.com/pandas-dev/pandas/)

## Motivations

`pandagg` is inspired by the official high level python client [elasticsearch-dsl](https://github.com/elastic/elasticsearch-dsl-py),
and is intended to make it more convenient to deal with deeply nested queries and aggregations.

The fundamental difference between those libraries is how they deal with the tree structure of aggregation queries
and their responses.

Suppose we have this aggregation structure: (types of agg don't matter). Let's call all of **A**, **B**, **C**, **D** our aggregation **nodes**, and the whole structure our **tree**.
```
A           (Terms agg)
└── B       (Filters agg)
    ├── C   (Avg agg)
    └── D   (Sum agg)
```


Question is who has the charge of storing the **tree structure** (how **nodes** are connected)?

In ***elasticsearch-dsl*** library, each aggregation **node** is responsible of knowing which are its direct children.

In ***pandagg***, all **nodes** are agnostic about which are their parents/children, and a **tree** object is in charge
of storing this structure. It is thus possible to add/update/remove aggregation **nodes** or **sub-trees** in
specific locations of the initial **tree**, thus allowing more flexible ways to build your queries.

Another difference is about how the response class. ***pandagg*** will favor "explicit" attributes and methods, rather
than automatically generated attributes (except for classes whose purpose is exclusively interactive).

### Disclaimers
***pandagg*** is not as mature as the official client, and some interfaces might change.

It does not ensure retro-compatible with previous versions of elasticsearch (intended to work with >=7). It is part
of the roadmap to tag ***pandagg*** versions according to the ElasticSearch versions they are related to (ie ***pandagg***
be v7.1.4 would work with ElasticSearch v7.X.X).

It doesn't provide yet all functionalities provided by the official client (for instance ORM like insert/updates, index
operations etc..). Primary focus of ***pandagg*** was on read operations.

## Contributing

All contributions, bug reports, bug fixes, documentation improvements, enhancements and ideas are welcome.


## Roadmap

- implement CI workflow: python2/3 tests, coverage
- documentation; explain challenges induced by nested `nodes` syntaxes: for instance why are nested query clauses
saved in `children` attribute before tree deserialization
- on aggregation `nodes`, ensure all allowed `fields` are listed
- expand functionalities: proper ORM similar to elasticsearch-dsl Document classes, index managing operations
- package versions for different ElasticSearch versions
