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
    graph = _make_graph(
        [
            {"id": "s1", "primitiveType": "pick", "handler": ""},
            {"id": "s2", "primitiveType": "place", "handler": ""},
            {"id": "s3", "primitiveType": "move_to", "handler": ""},
        ]
    )
    assign_handlers(graph)

    for sid in ["s1", "s2", "s3"]:
        assert graph.steps[sid].handler == "primitive", f"{sid} should be primitive"


def test_assign_handlers_contact_rich_policies() -> None:
    """Steps with linear_insert/press_fit/screw/guarded_move get handler='policy'."""
    graph = _make_graph(
        [
            {"id": "s1", "primitiveType": "linear_insert", "handler": ""},
            {"id": "s2", "primitiveType": "press_fit", "handler": ""},
            {"id": "s3", "primitiveType": "screw", "handler": ""},
            {"id": "s4", "primitiveType": "guarded_move", "handler": ""},
        ]
    )
    assign_handlers(graph)

    for sid in ["s1", "s2", "s3", "s4"]:
        assert graph.steps[sid].handler == "policy", f"{sid} should be policy"


def test_assign_handlers_preserves_existing() -> None:
    """primitive_type=None with handler already set is left unchanged."""
    graph = _make_graph(
        [
            {"id": "s1", "primitiveType": None, "handler": "policy"},
            {"id": "s2", "primitiveType": None, "handler": "primitive"},
        ]
    )
    assign_handlers(graph)

    assert graph.steps["s1"].handler == "policy"
    assert graph.steps["s2"].handler == "primitive"


def test_assign_handlers_defaults_missing() -> None:
    """primitive_type=None with no handler defaults to 'policy'."""
    graph = _make_graph(
        [
            {"id": "s1", "primitiveType": None, "handler": ""},
        ]
    )
    assign_handlers(graph)

    assert graph.steps["s1"].handler == "policy"


def test_assign_handlers_returns_same_graph() -> None:
    """assign_handlers mutates and returns the same graph object."""
    graph = _make_graph([{"id": "s1", "primitiveType": "pick", "handler": ""}])
    result = assign_handlers(graph)
    assert result is graph


# ---------------------------------------------------------------------------
# Assembly ordering tests
# ---------------------------------------------------------------------------


def test_cover_plates_assembled_last() -> None:
    """Thin, wide cover plates should be placed after internal parts."""
    from nextis.assembly.cad_parser import ParseResult
    from nextis.assembly.models import AssemblyGraph, Part
    from nextis.assembly.sequence_planner import SequencePlanner

    parts = {
        "ring_gear": Part(
            id="ring_gear",
            position=[0, 0, 0],
            geometry="box",
            dimensions=[0.066, 0.066, 0.024],
            color="#AAA",
        ),
        "satellite_gear": Part(
            id="satellite_gear",
            position=[0.02, 0.005, 0.01],
            geometry="box",
            dimensions=[0.014, 0.014, 0.01],
            color="#BBB",
        ),
        "sun_gear": Part(
            id="sun_gear",
            position=[0, 0.005, 0],
            geometry="sphere",
            dimensions=[0.013],
            color="#CCC",
        ),
        "carrier_top": Part(
            id="carrier_top",
            position=[0, 0.05, 0],
            geometry="box",
            dimensions=[0.042, 0.042, 0.004],  # thin + wide = cover
            color="#DDD",
        ),
    }

    graph = AssemblyGraph(id="test_gearbox", name="Test Gearbox", parts=parts)
    result = ParseResult(graph=graph, contacts=[])
    planned = SequencePlanner().plan(result)

    # Find the assembly/place steps (not pick steps)
    assemble_order: list[str] = []
    for sid in planned.step_order:
        step = planned.steps[sid]
        if step.name.startswith("Assemble") or step.name.startswith("Place"):
            assemble_order.append(step.part_ids[0])

    assert assemble_order[-1] == "carrier_top", (
        f"Cover plate should be last, got order: {assemble_order}"
    )


def test_vertical_ordering_bottom_up() -> None:
    """Parts lower in the assembly (smaller Y) should be assembled before higher."""
    from nextis.assembly.cad_parser import ParseResult
    from nextis.assembly.models import AssemblyGraph, Part
    from nextis.assembly.sequence_planner import SequencePlanner

    parts = {
        "base": Part(
            id="base",
            position=[0, 0, 0],
            geometry="box",
            dimensions=[0.1, 0.08, 0.1],
            color="#AAA",
        ),
        "low_part": Part(
            id="low_part",
            position=[0.01, 0.01, 0],
            geometry="box",
            dimensions=[0.02, 0.02, 0.02],
            color="#BBB",
        ),
        "high_part": Part(
            id="high_part",
            position=[0, 0.06, 0],
            geometry="box",
            dimensions=[0.02, 0.02, 0.02],
            color="#CCC",
        ),
    }

    graph = AssemblyGraph(id="test_vert", name="Test Vertical", parts=parts)
    result = ParseResult(graph=graph, contacts=[])
    planned = SequencePlanner().plan(result)

    assemble_order: list[str] = []
    for sid in planned.step_order:
        step = planned.steps[sid]
        if step.name.startswith("Assemble") or step.name.startswith("Place"):
            assemble_order.append(step.part_ids[0])

    low_idx = assemble_order.index("low_part")
    high_idx = assemble_order.index("high_part")
    assert low_idx < high_idx, f"Low part should come before high part, got: {assemble_order}"
