"""OpenWES Pick-Path Optimization Engine.

Provides modular warehouse route optimization algorithms:
- S-Shape / Snake Routing (Standard warehouse aisle traversal)
- Nearest-Neighbor TSP (Greedy euclidean distance heuristic)
- Zone-Based Coordinate Sequencing (Lexicographical aisle/bay/level order)
"""

import math
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseRouteOptimizer(ABC):
    """Abstract base class for warehouse pick-path optimizers."""

    @abstractmethod
    def optimize(
        self,
        tasks: List[Dict[str, Any]],
        start_point: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> List[Dict[str, Any]]:
        """Given a list of task dicts with location/coordinate info, return an ordered list with sequence numbers."""
        pass


def extract_coordinates(task: Dict[str, Any]) -> Tuple[float, float, float, str, int, int]:
    """Extract coordinates and aisle/bay indices from task or location code.

    Supports:
    - Explicit coordinates in `coord_x`, `coord_y`, `coord_z`
    - Parsing bin strings like 'A-02-03-01' -> Zone A, Aisle 2, Bay 3, Level 1
    """
    coords = task.get('coordinates') or {}
    x = float(coords.get('x', task.get('coord_x', 0.0)))
    y = float(coords.get('y', task.get('coord_y', 0.0)))
    z = float(coords.get('z', task.get('coord_z', 0.0)))

    loc_name = task.get('location_name') or task.get('location_code') or ''
    aisle_str = 'A'
    aisle_num = 1
    bay_num = 1

    # Parse formatted strings like A-02-05
    parts = loc_name.replace('_', '-').split('-')
    if parts:
        aisle_str = parts[0].strip().upper()
        if len(parts) >= 2 and parts[1].strip().isdigit():
            aisle_num = int(parts[1].strip())
        if len(parts) >= 3 and parts[2].strip().isdigit():
            bay_num = int(parts[2].strip())

    # If coordinates are 0, synthesize based on parsed layout
    if x == 0.0 and y == 0.0:
        # Aisle along X axis (spacing 3m), Bay along Y axis (spacing 1.5m)
        zone_offset = (ord(aisle_str[0]) - ord('A')) * 50.0 if aisle_str else 0.0
        x = zone_offset + (aisle_num * 3.0)
        y = bay_num * 1.5

    return x, y, z, aisle_str, aisle_num, bay_num


def euclidean_distance(
    p1: Tuple[float, float, float], p2: Tuple[float, float, float]
) -> float:
    """Calculate 3D Euclidean distance."""
    return math.sqrt(
        (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2
    )


def manhattan_distance(
    p1: Tuple[float, float, float], p2: Tuple[float, float, float]
) -> float:
    """Warehouse Manhattan aisle distance."""
    # Walking in grid aisles: dx + dy + vertical dz penalty
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) + (abs(p1[2] - p2[2]) * 1.5)


class SShapeOptimizer(BaseRouteOptimizer):
    """S-Shape (Snake) picking route optimizer.

    Traverses aisles sequentially:
    - Even aisles traversed in forward direction (e.g. Bay 1 -> Bay N)
    - Odd aisles traversed in reverse direction (e.g. Bay N -> Bay 1)
    Minimizes backtracking down warehouse aisles.
    """

    def optimize(
        self,
        tasks: List[Dict[str, Any]],
        start_point: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> List[Dict[str, Any]]:
        if not tasks:
            return []

        annotated = []
        for task in tasks:
            x, y, z, aisle_str, aisle_num, bay_num = extract_coordinates(task)
            annotated.append({
                'task': task,
                'x': x,
                'y': y,
                'z': z,
                'aisle_str': aisle_str,
                'aisle_num': aisle_num,
                'bay_num': bay_num,
            })

        # Group by (aisle_str, aisle_num)
        def sort_key(item):
            # Sort by zone, then aisle
            # In alternating aisles, reverse bay ordering
            aisle_parity = item['aisle_num'] % 2
            effective_bay = item['bay_num'] if aisle_parity == 1 else -item['bay_num']
            return (item['aisle_str'], item['aisle_num'], effective_bay, item['z'])

        sorted_items = sorted(annotated, key=sort_key)

        result = []
        total_dist = 0.0
        curr_pt = start_point

        for idx, item in enumerate(sorted_items, start=1):
            t = dict(item['task'])
            t['sequence'] = idx
            target_pt = (item['x'], item['y'], item['z'])
            dist = manhattan_distance(curr_pt, target_pt)
            total_dist += dist
            t['segment_distance'] = round(dist, 2)
            t['cumulative_distance'] = round(total_dist, 2)
            t['optimized_coords'] = {'x': item['x'], 'y': item['y'], 'z': item['z']}
            curr_pt = target_pt
            result.append(t)

        return result


class NearestNeighborOptimizer(BaseRouteOptimizer):
    """Greedy Nearest-Neighbor TSP pick-path optimizer.

    Starting from depot / start position, visits the nearest unvisited location.
    """

    def optimize(
        self,
        tasks: List[Dict[str, Any]],
        start_point: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> List[Dict[str, Any]]:
        if not tasks:
            return []

        remaining = []
        for task in tasks:
            x, y, z, aisle_str, aisle_num, bay_num = extract_coordinates(task)
            remaining.append({
                'task': task,
                'point': (x, y, z),
            })

        curr_pt = start_point
        total_dist = 0.0
        result = []
        seq = 1

        while remaining:
            # Find closest item to current position
            best_idx = 0
            best_dist = float('inf')
            for idx, cand in enumerate(remaining):
                d = manhattan_distance(curr_pt, cand['point'])
                if d < best_dist:
                    best_dist = d
                    best_idx = idx

            chosen = remaining.pop(best_idx)
            total_dist += best_dist

            t = dict(chosen['task'])
            t['sequence'] = seq
            t['segment_distance'] = round(best_dist, 2)
            t['cumulative_distance'] = round(total_dist, 2)
            t['optimized_coords'] = {
                'x': chosen['point'][0],
                'y': chosen['point'][1],
                'z': chosen['point'][2],
            }
            result.append(t)

            curr_pt = chosen['point']
            seq += 1

        return result


class ZoneCoordinateOptimizer(BaseRouteOptimizer):
    """Lexicographical Zone -> Aisle -> Bay -> Level sequence ordering."""

    def optimize(
        self,
        tasks: List[Dict[str, Any]],
        start_point: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> List[Dict[str, Any]]:
        if not tasks:
            return []

        annotated = []
        for task in tasks:
            x, y, z, aisle_str, aisle_num, bay_num = extract_coordinates(task)
            annotated.append({
                'task': task,
                'x': x,
                'y': y,
                'z': z,
                'key': (aisle_str, aisle_num, bay_num, z),
            })

        sorted_items = sorted(annotated, key=lambda i: i['key'])
        result = []
        curr_pt = start_point
        total_dist = 0.0

        for idx, item in enumerate(sorted_items, start=1):
            t = dict(item['task'])
            t['sequence'] = idx
            target_pt = (item['x'], item['y'], item['z'])
            dist = manhattan_distance(curr_pt, target_pt)
            total_dist += dist
            t['segment_distance'] = round(dist, 2)
            t['cumulative_distance'] = round(total_dist, 2)
            t['optimized_coords'] = {'x': item['x'], 'y': item['y'], 'z': item['z']}
            curr_pt = target_pt
            result.append(t)

        return result


# Optimization algorithm registry
OPTIMIZERS = {
    'S_SHAPE': SShapeOptimizer(),
    'NEAREST_NEIGHBOR': NearestNeighborOptimizer(),
    'ZONAL': ZoneCoordinateOptimizer(),
}


def optimize_pick_path(
    tasks: List[Dict[str, Any]],
    strategy: str = 'S_SHAPE',
    start_point: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Tuple[List[Dict[str, Any]], float]:
    """Execute pick path optimization with the designated algorithm."""
    optimizer = OPTIMIZERS.get(strategy.upper(), SShapeOptimizer())
    ordered_tasks = optimizer.optimize(tasks, start_point)
    total_distance = ordered_tasks[-1]['cumulative_distance'] if ordered_tasks else 0.0
    return ordered_tasks, total_distance
