"""A small example knowledge graph (SQL interview concepts).

Swap this for your own domain YAML later; the engine is domain-agnostic.
"""

from .graph import ConceptGraph
from .models import Concept

SQL_CONCEPTS = [
    Concept("select", "SELECT basics", difficulty=0.1),
    Concept("where", "Filtering with WHERE", prerequisites=("select",), difficulty=0.2),
    Concept("group_by", "GROUP BY", prerequisites=("select",), difficulty=0.4),
    Concept("aggregates", "Aggregate functions", prerequisites=("group_by",), difficulty=0.4),
    Concept("having", "HAVING", prerequisites=("aggregates", "where"), difficulty=0.5),
    Concept("joins", "JOINs", prerequisites=("select", "where"), difficulty=0.5),
    Concept("subqueries", "Subqueries", prerequisites=("joins", "where"), difficulty=0.6),
    Concept("window", "Window functions", prerequisites=("group_by", "aggregates"), difficulty=0.8),
    Concept("ctes", "CTEs", prerequisites=("subqueries",), difficulty=0.7),
]


def sql_graph() -> ConceptGraph:
    return ConceptGraph(SQL_CONCEPTS)
