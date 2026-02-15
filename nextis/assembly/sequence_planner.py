"""Sequence planner: parsed parts + contacts → assembly steps.

Takes the output of CADParser and generates a heuristic assembly sequence.
Targets ~70% correct — user reviews and adjusts via the frontend.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from nextis.assembly.cad_parser import ParseResult
from nextis.assembly.models import AssemblyGraph, AssemblyStep, SuccessCriteria
from nextis.errors import AssemblyError

logger = logging.getLogger(__name__)

# Volume threshold (m³) below which a part is considered "small"
_SMALL_PART_VOLUME = 1e-6  # ~10mm cube


class SequencePlanner:
    """Generate assembly steps and execution order from parsed CAD data.

    Sorts parts by size, assigns primitive types based on geometry
    heuristics, and wires dependencies. Tight-tolerance contacts are
    flagged as handler="policy" (needs teaching).

    Args:
        tight_tolerance: Contact clearance (metres) below which a step
            requires a learned policy instead of a primitive.
    """

    def __init__(self, tight_tolerance: float = 0.0001) -> None:
        self._tight_tolerance = tight_tolerance

    def plan(self, parse_result: ParseResult) -> AssemblyGraph:
        """Generate steps and step_order for a parsed assembly.

        Args:
            parse_result: Output from CADParser.parse().

        Returns:
            The same AssemblyGraph with steps and step_order populated.

        Raises:
            AssemblyError: If the graph has no parts.
        """
        graph = parse_result.graph
        contacts = parse_result.contacts

        if not graph.parts:
            raise AssemblyError("Cannot plan assembly with no parts")

        # Build contact adjacency
        adjacency: dict[str, set[str]] = defaultdict(set)
        for a, b in contacts:
            adjacency[a].add(b)
            adjacency[b].add(a)

        # Sort parts using geometric heuristics (base first, covers last)
        sorted_parts = _compute_assembly_order(graph.parts)

        steps: dict[str, AssemblyStep] = {}
        step_num = 0

        # Base part: place it first (no pick needed)
        base = sorted_parts[0]
        base.is_base = True
        step_num += 1
        base_step_id = f"step_{step_num:03d}"
        steps[base_step_id] = AssemblyStep(
            id=base_step_id,
            name=f"Place {base.id} as base",
            part_ids=[base.id],
            dependencies=[],
            handler="primitive",
            primitive_type="place",
            primitive_params={"part_id": base.id},
            success_criteria=SuccessCriteria(type="position"),
        )
        prev_assembly_step = base_step_id

        # Remaining parts: pick + assemble
        for part in sorted_parts[1:]:
            # Pick step
            step_num += 1
            pick_id = f"step_{step_num:03d}"
            steps[pick_id] = AssemblyStep(
                id=pick_id,
                name=f"Pick {part.id}",
                part_ids=[part.id],
                dependencies=[prev_assembly_step],
                handler="primitive",
                primitive_type="pick",
                primitive_params={"part_id": part.id},
                success_criteria=SuccessCriteria(type="force_threshold", threshold=0.5),
            )

            # Assembly step — type depends on geometry + contacts
            step_num += 1
            asm_id = f"step_{step_num:03d}"
            handler, prim_type, criteria = self._classify_assembly_action(
                part, adjacency.get(part.id, set())
            )

            # Parts involved: this part + any it contacts
            involved = [part.id]
            for contact_id in adjacency.get(part.id, set()):
                if contact_id not in involved:
                    involved.append(contact_id)

            steps[asm_id] = AssemblyStep(
                id=asm_id,
                name=f"Assemble {part.id}",
                part_ids=involved,
                dependencies=[pick_id],
                handler=handler,
                primitive_type=prim_type if handler == "primitive" else None,
                primitive_params={"part_id": part.id} if handler == "primitive" else None,
                policy_id=None,
                success_criteria=criteria,
            )
            prev_assembly_step = asm_id

        # Topological sort
        step_order = self._topological_sort(steps)

        graph.steps = steps
        graph.step_order = step_order

        # Recompute layout positions now that step_order is available
        from nextis.assembly.layout import compute_layout_positions

        compute_layout_positions(graph)

        logger.info(
            "Planned %d steps for assembly '%s' (%d parts)",
            len(steps),
            graph.id,
            len(graph.parts),
        )
        return graph

    def _classify_assembly_action(
        self,
        part: object,
        contacts: set[str],
    ) -> tuple[str, str | None, SuccessCriteria]:
        """Determine handler, primitive type, and criteria for a part.

        Returns:
            (handler, primitive_type, success_criteria)
        """
        from nextis.assembly.models import Part

        assert isinstance(part, Part)

        geo = part.geometry or "box"
        dims = part.dimensions or [0.05, 0.05, 0.05]
        vol = _part_volume(part)

        # Cylinder with contacts → check tolerance
        if geo == "cylinder" and contacts:
            # Small radius cylinders always need policy (pins, shafts)
            if len(dims) >= 2 and dims[0] < 0.008:
                return ("policy", None, SuccessCriteria(type="classifier"))
            # Larger cylinders with contacts → linear_insert primitive
            return (
                "primitive",
                "linear_insert",
                SuccessCriteria(type="force_signature", pattern="snap_fit"),
            )

        # Parts with many contacts → likely needs precise alignment → policy
        if len(contacts) >= 3:
            return ("policy", None, SuccessCriteria(type="classifier"))

        # "gear" or "bearing" in part name → likely needs teaching
        name_lower = part.id.lower()
        if any(kw in name_lower for kw in ("gear", "bearing", "ring", "snap", "clip")) and contacts:
            return (
                "policy",
                None,
                SuccessCriteria(type="force_signature", pattern="meshing"),
            )

        # Very small part → press_fit (likely fastener)
        if vol < _SMALL_PART_VOLUME:
            return (
                "primitive",
                "press_fit",
                SuccessCriteria(type="force_threshold", threshold=15.0),
            )

        # Small cylinder without contacts → might need teaching
        if geo == "cylinder" and len(dims) >= 2 and dims[0] < 0.005:
            return (
                "policy",
                None,
                SuccessCriteria(type="classifier"),
            )

        # Default: place
        return (
            "primitive",
            "place",
            SuccessCriteria(type="position"),
        )

    @staticmethod
    def _topological_sort(steps: dict[str, AssemblyStep]) -> list[str]:
        """Kahn's algorithm for topological ordering of steps.

        Args:
            steps: Step definitions keyed by step ID.

        Returns:
            List of step IDs in execution order.

        Raises:
            AssemblyError: If the dependency graph has a cycle.
        """
        in_degree: dict[str, int] = {sid: 0 for sid in steps}
        children: dict[str, list[str]] = defaultdict(list)

        for sid, step in steps.items():
            for dep in step.dependencies:
                if dep in steps:
                    children[dep].append(sid)
                    in_degree[sid] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        queue.sort()  # deterministic ordering
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for child in sorted(children[node]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(result) != len(steps):
            raise AssemblyError("Cycle detected in step dependency graph")

        return result


_PRIMITIVE_HANDLER_TYPES = {"move_to", "pick", "place"}
_POLICY_HANDLER_TYPES = {"linear_insert", "press_fit", "screw", "guarded_move"}


def assign_handlers(graph: AssemblyGraph) -> AssemblyGraph:
    """Auto-assign step handlers based on primitive_type.

    Rules:
        - move_to / pick / place -> handler="primitive" (geometric motions).
        - linear_insert / press_fit / screw / guarded_move -> handler="policy"
          (contact-rich tasks that benefit from learned policies).
        - primitive_type is None and handler already set -> unchanged.
        - primitive_type is None and handler is missing -> default to "policy".

    Args:
        graph: Assembly graph to update (mutated in-place).

    Returns:
        The same graph with updated handlers.
    """
    for step in graph.steps.values():
        if step.primitive_type in _PRIMITIVE_HANDLER_TYPES:
            step.handler = "primitive"
        elif step.primitive_type in _POLICY_HANDLER_TYPES or (
            step.primitive_type is None and not step.handler
        ):
            step.handler = "policy"
    return graph


def _compute_assembly_order(parts: dict[str, object]) -> list[object]:
    """Sort parts into assembly order using geometric heuristics.

    Rules (applied in priority order):
        1. Base part (largest volume, excluding covers) always first.
        2. Cover/lid parts (thin + wide) always last.
        3. Interior parts sorted by vertical position (Y ascending, bottom-up),
           ties broken by volume descending.

    Args:
        parts: Part catalog keyed by ID.

    Returns:
        Parts sorted in assembly order.
    """
    part_list = list(parts.values())
    if len(part_list) <= 1:
        return part_list

    # Separate covers from non-covers
    covers: list[object] = []
    non_covers: list[object] = []
    for p in part_list:
        if _is_cover(p):
            covers.append(p)
        else:
            non_covers.append(p)

    # Base = largest non-cover by volume
    if non_covers:
        base = max(non_covers, key=lambda p: _part_volume(p))
        interior = [p for p in non_covers if p.id != base.id]  # type: ignore[union-attr]
    else:
        # All parts are covers — pick largest as base
        base = max(covers, key=lambda p: _part_volume(p))
        covers = [p for p in covers if p.id != base.id]  # type: ignore[union-attr]
        interior = []

    # Sort interior by Y position ascending (bottom-up), then volume descending
    interior.sort(key=lambda p: (_assembly_height(p), -_part_volume(p)))

    # Sort covers by Y ascending
    covers.sort(key=lambda p: (_assembly_height(p), -_part_volume(p)))

    return [base] + interior + covers


def _is_cover(part: object) -> bool:
    """Detect if a part is a cover/lid (thin + wide).

    A cover has one dimension much smaller than the others (flatness < 0.15)
    and is not a known internal part type (bearing, gear, etc.).

    Args:
        part: Part to classify.

    Returns:
        True if the part appears to be a cover or lid.
    """
    from nextis.assembly.models import Part

    assert isinstance(part, Part)

    dims = part.dimensions or [0.05, 0.05, 0.05]
    if len(dims) < 3:
        return False

    # Internal parts are never covers regardless of shape
    name = part.id.lower()
    if any(kw in name for kw in ("bearing", "gear", "pin", "shaft", "ring", "bushing")):
        return False

    sorted_dims = sorted(dims)
    if sorted_dims[2] < 1e-9:
        return False
    flatness = sorted_dims[0] / sorted_dims[2]
    return flatness < 0.15


def _assembly_height(part: object) -> float:
    """Get the vertical position (Y coordinate) of a part for sorting.

    Args:
        part: Part to query.

    Returns:
        Y-coordinate of the part's assembled position.
    """
    from nextis.assembly.models import Part

    assert isinstance(part, Part)
    pos = part.position or [0.0, 0.0, 0.0]
    return pos[1]


def _part_volume(part: object) -> float:
    """Estimate part volume from its dimensions."""
    from nextis.assembly.models import Part

    assert isinstance(part, Part)

    dims = part.dimensions or [0.05, 0.05, 0.05]
    if len(dims) == 1:
        # Sphere: 4/3 π r³
        return (4 / 3) * 3.14159 * dims[0] ** 3
    if len(dims) == 2:
        # Cylinder: π r² h
        return 3.14159 * dims[0] ** 2 * dims[1]
    # Box: w * h * d
    return dims[0] * dims[1] * dims[2] if len(dims) >= 3 else 0.0
