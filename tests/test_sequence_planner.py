"""Tests for handler auto-assignment in sequence_planner."""

from __future__ import annotations

from nextis.assembly.models import AssemblyGraph
from nextis.assembly.sequence_planner import assign_handlers


def _make_graph(steps_data: list[dict]) -> AssemblyGraph:
    """Build a minimal AssemblyGraph from a list of step dicts."""
    steps = {}
    order = []
    for s in steps_data:
        sid = s["id"]
        steps[sid] = {
            "id": sid,
            "name": s.get("name", sid),
            "partIds": ["part_a"],
            "dependencies": [],
            "handler": s.get("handler", ""),
            "primitiveType": s.get("primitiveType"),
            "primitiveParams": None,
            "policyId": None,
            "successCriteria": {"type": "position"},
            "maxRetries": 1,
        }
        order.append(sid)

    data = {
        "id": "test",
        "name": "Test",
        "parts": {
            "part_a": {
                "id": "part_a",
                "cadFile": None,
                "meshFile": None,
                "graspPoints": [],
                "position": [0, 0, 0],
                "geometry": "box",
                "dimensions": [0.05, 0.05, 0.05],
                "color": "#AAA",
            },
        },
        "steps": steps,
        "stepOrder": order,
    }
    return AssemblyGraph.model_validate(data)


def test_assign_handlers_geometric_primitives() -> None:
    """Steps with pick/place/move_to get handler='primitive'."""
    graph = _make_graph([
        {"id": "s1", "primitiveType": "pick", "handler": ""},
        {"id": "s2", "primitiveType": "place", "handler": ""},
        {"id": "s3", "primitiveType": "move_to", "handler": ""},
    ])
    assign_handlers(graph)

    for sid in ["s1", "s2", "s3"]:
        assert graph.steps[sid].handler == "primitive", f"{sid} should be primitive"


def test_assign_handlers_contact_rich_policies() -> None:
    """Steps with linear_insert/press_fit/screw/guarded_move get handler='policy'."""
    graph = _make_graph([
        {"id": "s1", "primitiveType": "linear_insert", "handler": ""},
        {"id": "s2", "primitiveType": "press_fit", "handler": ""},
        {"id": "s3", "primitiveType": "screw", "handler": ""},
        {"id": "s4", "primitiveType": "guarded_move", "handler": ""},
    ])
    assign_handlers(graph)

    for sid in ["s1", "s2", "s3", "s4"]:
        assert graph.steps[sid].handler == "policy", f"{sid} should be policy"


def test_assign_handlers_preserves_existing() -> None:
    """primitive_type=None with handler already set is left unchanged."""
    graph = _make_graph([
        {"id": "s1", "primitiveType": None, "handler": "policy"},
        {"id": "s2", "primitiveType": None, "handler": "primitive"},
    ])
    assign_handlers(graph)

    assert graph.steps["s1"].handler == "policy"
    assert graph.steps["s2"].handler == "primitive"


def test_assign_handlers_defaults_missing() -> None:
    """primitive_type=None with no handler defaults to 'policy'."""
    graph = _make_graph([
        {"id": "s1", "primitiveType": None, "handler": ""},
    ])
    assign_handlers(graph)

    assert graph.steps["s1"].handler == "policy"


def test_assign_handlers_returns_same_graph() -> None:
    """assign_handlers mutates and returns the same graph object."""
    graph = _make_graph([{"id": "s1", "primitiveType": "pick", "handler": ""}])
    result = assign_handlers(graph)
    assert result is graph
