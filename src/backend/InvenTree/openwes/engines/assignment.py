"""OpenWES Extensible Task Assignment Engine.

Calculates multi-criteria assignment scores to pair pending warehouse tasks
with optimal active warehouse operators based on:
- Distance / Proximity to source location
- Current Operator Workload (in-progress and assigned queue)
- Task Priority
- Zone Match / Zone affinity
- Operator Availability status
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from django.contrib.auth import get_user_model
from django.utils import timezone

from openwes.models import (
    OperatorSession,
    TaskAssignment,
    WarehouseLocationMeta,
    WarehouseTask,
    WarehouseZone,
)
from openwes.status_codes import OperatorStatus, WarehouseTaskStatus


@dataclass
class AssignmentScoreBreakdown:
    operator_id: int
    operator_username: str
    total_score: float
    distance_score: float
    workload_score: float
    priority_score: float
    zone_score: float
    reason: str


class TaskAssignmentEngine:
    """Configurable, multi-factor warehouse task assignment engine."""

    def __init__(
        self,
        distance_weight: float = 0.35,
        workload_weight: float = 0.30,
        priority_weight: float = 0.20,
        zone_weight: float = 0.15,
    ):
        self.distance_weight = distance_weight
        self.workload_weight = workload_weight
        self.priority_weight = priority_weight
        self.zone_weight = zone_weight

    def calculate_distance(
        self, task: WarehouseTask, session: Optional[OperatorSession]
    ) -> float:
        """Calculate approximate distance between operator's last zone/task and new task location."""
        if not task.source_location:
            return 20.0  # neutral distance

        task_meta = getattr(task.source_location, 'openwes_meta', None)
        task_x = task_meta.coord_x if task_meta else 10.0
        task_y = task_meta.coord_y if task_meta else 10.0

        op_x = 0.0
        op_y = 0.0

        if session and session.current_task and session.current_task.source_location:
            op_meta = getattr(session.current_task.source_location, 'openwes_meta', None)
            if op_meta:
                op_x = op_meta.coord_x
                op_y = op_meta.coord_y
        elif session and session.current_zone:
            # Approximate zone center
            zone_code = session.current_zone.code.upper()
            zone_offset = (ord(zone_code[-1]) - ord('A')) * 30.0 if zone_code else 0.0
            op_x = zone_offset
            op_y = 15.0

        return math.sqrt((task_x - op_x) ** 2 + (task_y - op_y) ** 2)

    def evaluate_operator(
        self, task: WarehouseTask, operator, session: Optional[OperatorSession]
    ) -> AssignmentScoreBreakdown:
        """Score an operator for a specific task. Lower score = better candidate."""
        # 1. Availability check
        if session and session.status in [OperatorStatus.OFFLINE, OperatorStatus.BREAK]:
            return AssignmentScoreBreakdown(
                operator_id=operator.id,
                operator_username=operator.username,
                total_score=9999.0,
                distance_score=999.0,
                workload_score=999.0,
                priority_score=0.0,
                zone_score=999.0,
                reason='Operator is currently offline or on break.',
            )

        # 2. Current workload (assigned or in-progress tasks)
        active_tasks = WarehouseTask.objects.filter(
            assigned_operator=operator,
            status__in=[WarehouseTaskStatus.ASSIGNED, WarehouseTaskStatus.IN_PROGRESS],
        ).count()
        # Scale workload: 0 tasks = 0, 5 tasks = 50, capped at 100
        raw_workload = min(100.0, active_tasks * 15.0)

        # 3. Distance estimation
        dist_meters = self.calculate_distance(task, session)
        raw_dist = min(100.0, dist_meters * 1.5)

        # 4. Task priority impact
        # High priority tasks deduct from score to favor immediate dispatch
        raw_priority = float(task.priority) * 2.0

        # 5. Zone match
        zone_penalty = 0.0
        if task.source_location and hasattr(task.source_location, 'openwes_meta'):
            task_zone = task.source_location.openwes_meta.zone
            if session and session.current_zone and task_zone:
                if session.current_zone.id == task_zone.id:
                    zone_penalty = -25.0  # bonus for matching current zone
                else:
                    zone_penalty = 25.0   # penalty for cross-zone travel

        total_score = (
            (self.distance_weight * raw_dist)
            + (self.workload_weight * raw_workload)
            - (self.priority_weight * raw_priority)
            + (self.zone_weight * zone_penalty)
        )

        reasons = []
        if raw_workload == 0:
            reasons.append('Operator queue empty')
        else:
            reasons.append(f'{active_tasks} active tasks in queue')

        if zone_penalty < 0:
            reasons.append('Active in same warehouse zone')
        elif zone_penalty > 0:
            reasons.append('Requires cross-zone transit')

        reasons.append(f'Approx {dist_meters:.1f}m travel distance')

        return AssignmentScoreBreakdown(
            operator_id=operator.id,
            operator_username=operator.username,
            total_score=round(total_score, 2),
            distance_score=round(raw_dist, 2),
            workload_score=round(raw_workload, 2),
            priority_score=round(raw_priority, 2),
            zone_score=round(zone_penalty, 2),
            reason='; '.join(reasons),
        )

    def assign_task(
        self, task: WarehouseTask, candidate_operators=None
    ) -> Optional[TaskAssignment]:
        """Evaluate candidates, pick the highest-affinity operator, and record the assignment."""
        User = get_user_model()
        if candidate_operators is None:
            # Prefer operators with active online sessions, or any active users
            sessions = OperatorSession.objects.filter(
                status__in=[OperatorStatus.ONLINE, OperatorStatus.PICKING, OperatorStatus.IDLE]
            ).select_related('operator', 'current_zone', 'current_task')

            if sessions.exists():
                candidate_operators = [s.operator for s in sessions]
            else:
                candidate_operators = list(User.objects.filter(is_active=True)[:10])

        if not candidate_operators:
            return None

        # Fetch sessions map
        sessions_map = {
            s.operator_id: s
            for s in OperatorSession.objects.filter(operator__in=candidate_operators).select_related('current_zone', 'current_task')
        }

        evaluations = []
        for op in candidate_operators:
            session = sessions_map.get(op.id)
            breakdown = self.evaluate_operator(task, op, session)
            evaluations.append((op, breakdown))

        # Sort by total_score ascending (lowest score is best)
        evaluations.sort(key=lambda x: x[1].total_score)
        best_operator, best_breakdown = evaluations[0]

        # Apply assignment to task
        task.assign(best_operator, save=True)

        # Record explainable assignment
        assignment, _ = TaskAssignment.objects.update_or_create(
            task=task,
            defaults={
                'operator': best_operator,
                'score': best_breakdown.total_score,
                'distance_score': best_breakdown.distance_score,
                'workload_score': best_breakdown.workload_score,
                'priority_score': best_breakdown.priority_score,
                'zone_score': best_breakdown.zone_score,
                'reason': best_breakdown.reason,
            },
        )
        return assignment
