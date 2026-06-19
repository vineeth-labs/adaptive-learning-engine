import pytest

from backend.services.graph.concept_graph import Concept, ConceptGraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_concept(id: str, prereqs: tuple[str, ...] = (), difficulty: float = 0.5) -> Concept:
    return Concept(id=id, name=id.capitalize(), prerequisites=prereqs, difficulty=difficulty)


def linear_chain() -> list[Concept]:
    """A → B → C"""
    return [
        make_concept("A"),
        make_concept("B", prereqs=("A",)),
        make_concept("C", prereqs=("B",)),
    ]


def diamond_graph() -> list[Concept]:
    """A → B, A → C, B → D, C → D"""
    return [
        make_concept("A"),
        make_concept("B", prereqs=("A",)),
        make_concept("C", prereqs=("A",)),
        make_concept("D", prereqs=("B", "C")),
    ]


# ---------------------------------------------------------------------------
# Concept validation
# ---------------------------------------------------------------------------

class TestConceptValidation:
    def test_difficulty_at_zero_valid(self):
        c = make_concept("X", difficulty=0.0)
        assert c.difficulty == 0.0

    def test_difficulty_at_one_valid(self):
        c = make_concept("X", difficulty=1.0)
        assert c.difficulty == 1.0

    def test_difficulty_in_range_valid(self):
        c = make_concept("X", difficulty=0.3)
        assert c.difficulty == 0.3

    def test_difficulty_below_zero_raises(self):
        with pytest.raises(ValueError, match="difficulty"):
            make_concept("X", difficulty=-0.1)

    def test_difficulty_above_one_raises(self):
        with pytest.raises(ValueError, match="difficulty"):
            make_concept("X", difficulty=1.01)


# ---------------------------------------------------------------------------
# ConceptGraph construction
# ---------------------------------------------------------------------------

class TestConceptGraphConstruction:
    def test_happy_path(self):
        graph = ConceptGraph(linear_chain())
        assert set(graph.concepts) == {"A", "B", "C"}

    def test_empty_graph(self):
        graph = ConceptGraph([])
        assert graph.concepts == []

    def test_single_node(self):
        graph = ConceptGraph([make_concept("A")])
        assert graph.concepts == ["A"]

    def test_duplicate_id_raises(self):
        concepts = [make_concept("A"), make_concept("A")]
        with pytest.raises(ValueError, match="duplicate"):
            ConceptGraph(concepts)

    def test_unknown_prerequisite_raises(self):
        concepts = [make_concept("B", prereqs=("MISSING",))]
        with pytest.raises(ValueError, match="unknown prerequisite"):
            ConceptGraph(concepts)

    def test_cycle_detection_simple(self):
        # A → B → A
        concepts = [
            make_concept("A", prereqs=("B",)),
            make_concept("B", prereqs=("A",)),
        ]
        with pytest.raises(ValueError, match="cycle"):
            ConceptGraph(concepts)

    def test_cycle_detection_longer(self):
        # A → B → C → A
        concepts = [
            make_concept("A", prereqs=("C",)),
            make_concept("B", prereqs=("A",)),
            make_concept("C", prereqs=("B",)),
        ]
        with pytest.raises(ValueError, match="cycle"):
            ConceptGraph(concepts)


# ---------------------------------------------------------------------------
# Topological order
# ---------------------------------------------------------------------------

class TestTopologicalOrder:
    def test_linear_chain_order(self):
        graph = ConceptGraph(linear_chain())
        order = graph.topological_order()
        assert order.index("A") < order.index("B") < order.index("C")

    def test_diamond_order(self):
        graph = ConceptGraph(diamond_graph())
        order = graph.topological_order()
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_all_concepts_present(self):
        graph = ConceptGraph(diamond_graph())
        assert set(graph.topological_order()) == {"A", "B", "C", "D"}

    def test_deterministic(self):
        graph = ConceptGraph(diamond_graph())
        assert graph.topological_order() == graph.topological_order()


# ---------------------------------------------------------------------------
# ancestors()
# ---------------------------------------------------------------------------

class TestAncestors:
    def test_ancestors_linear(self):
        graph = ConceptGraph(linear_chain())
        assert graph.ancestors("C") == {"A", "B"}

    def test_ancestors_one_hop(self):
        graph = ConceptGraph(linear_chain())
        assert graph.ancestors("B") == {"A"}

    def test_ancestors_root_empty(self):
        graph = ConceptGraph(linear_chain())
        assert graph.ancestors("A") == set()

    def test_ancestors_diamond(self):
        graph = ConceptGraph(diamond_graph())
        assert graph.ancestors("D") == {"A", "B", "C"}

    def test_ancestors_mid_diamond(self):
        graph = ConceptGraph(diamond_graph())
        assert graph.ancestors("B") == {"A"}
        assert graph.ancestors("C") == {"A"}


# ---------------------------------------------------------------------------
# descendants()
# ---------------------------------------------------------------------------

class TestDescendants:
    def test_descendants_linear(self):
        graph = ConceptGraph(linear_chain())
        assert graph.descendants("A") == {"B", "C"}

    def test_descendants_one_hop(self):
        graph = ConceptGraph(linear_chain())
        assert graph.descendants("B") == {"C"}

    def test_descendants_leaf_empty(self):
        graph = ConceptGraph(linear_chain())
        assert graph.descendants("C") == set()

    def test_descendants_diamond_root(self):
        graph = ConceptGraph(diamond_graph())
        assert graph.descendants("A") == {"B", "C", "D"}

    def test_descendants_diamond_mid(self):
        graph = ConceptGraph(diamond_graph())
        assert graph.descendants("B") == {"D"}
        assert graph.descendants("C") == {"D"}


# ---------------------------------------------------------------------------
# direct_dependents() and prerequisites()
# ---------------------------------------------------------------------------

class TestAdjacency:
    def test_direct_dependents_not_transitive(self):
        # A → B → C: direct dependents of A should be only B, not C
        graph = ConceptGraph(linear_chain())
        assert graph.direct_dependents("A") == ["B"]

    def test_direct_dependents_diamond(self):
        graph = ConceptGraph(diamond_graph())
        assert set(graph.direct_dependents("A")) == {"B", "C"}

    def test_direct_dependents_leaf(self):
        graph = ConceptGraph(linear_chain())
        assert graph.direct_dependents("C") == []

    def test_prerequisites_accessor(self):
        graph = ConceptGraph(linear_chain())
        assert graph.prerequisites("B") == ("A",)

    def test_prerequisites_root(self):
        graph = ConceptGraph(linear_chain())
        assert graph.prerequisites("A") == ()

    def test_prerequisites_multiple(self):
        graph = ConceptGraph(diamond_graph())
        assert set(graph.prerequisites("D")) == {"B", "C"}
