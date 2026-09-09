"""OpenWES Offline-First Synchronization & Idempotency Engine.

Handles batch event synchronization from mobile/tablet clients operating in offline mode:
- Deduplicates incoming events using event_id and client idempotency_key.
- Ensures zero duplicate inventory deductions across network retries.
- Handles edge cases: stale tasks, conflicts, partial batch sync, server validation.
"""

import logging
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Tuple
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from openwes.models import (
    SyncEvent,
    WarehouseAuditEvent,
    WarehouseException,
    WarehouseTask,
)
from openwes.status_codes import (
    AuditEventType,
    ExceptionType,
    SyncStatus,
    WarehouseTaskStatus,
)

logger = logging.getLogger('openwes')


class SyncEngine:
    """Transactional, idempotent event synchronization processor."""

    @classmethod
    @transaction.atomic
    def process_sync_batch(
        cls, events: List[Dict[str, Any]], operator=None, device_id: str = ''
    ) -> Dict[str, Any]:
        """Process a list of offline event objects with transactional safety.

        Returns detailed per-event receipt statuses:
        {
            "synced_count": 3,
            "duplicate_count": 1,
            "conflict_count": 0,
            "results": [ ... ]
        }
        """
        results = []
        synced_count = 0
        duplicate_count = 0
        conflict_count = 0
        rejected_count = 0

        for raw_event in events:
            ev_id = raw_event.get('event_id')
            idempotency_key = raw_event.get('idempotency_key') or str(ev_id)
            event_type = raw_event.get('event_type')
            payload = raw_event.get('payload', {})

            # 1. Check if event_id or idempotency_key has already been processed
            existing_event = None
            if ev_id:
                try:
                    uuid_val = uuid.UUID(str(ev_id))
                    existing_event = SyncEvent.objects.filter(event_id=uuid_val).first()
                except (ValueError, TypeError):
                    pass

            if not existing_event and idempotency_key:
                existing_event = SyncEvent.objects.filter(
                    idempotency_key=idempotency_key
                ).first()

            if existing_event:
                # Idempotent match: return previous processing outcome without repeating side effects
                duplicate_count += 1
                results.append({
                    'event_id': str(existing_event.event_id),
                    'idempotency_key': existing_event.idempotency_key,
                    'status': existing_event.status,
                    'message': 'Duplicate event acknowledged idempotently.',
                    'processed_at': existing_event.processed_at.isoformat()
                    if existing_event.processed_at
                    else None,
                    'is_duplicate': True,
                })
                continue

            # 2. Create sync record in RECEIVED state
            try:
                event_uuid = uuid.UUID(str(ev_id)) if ev_id else uuid.uuid4()
            except (ValueError, TypeError):
                event_uuid = uuid.uuid4()

            sync_record = SyncEvent.objects.create(
                event_id=event_uuid,
                idempotency_key=idempotency_key,
                operator=operator,
                device_id=device_id or raw_event.get('device_id', ''),
                event_type=event_type,
                payload=payload,
                status=SyncStatus.RECEIVED,
            )

            # 3. Dispatch to specific event handler
            handler_method = getattr(cls, f'_handle_{event_type.lower()}', None)
            if not handler_method:
                sync_record.status = SyncStatus.REJECTED
                sync_record.error_message = f'Unknown event type: {event_type}'
                sync_record.processed_at = timezone.now()
                sync_record.save()
                rejected_count += 1
                results.append({
                    'event_id': str(sync_record.event_id),
                    'idempotency_key': idempotency_key,
                    'status': SyncStatus.REJECTED,
                    'error': sync_record.error_message,
                })
                continue

            try:
                outcome_status, message = handler_method(payload, operator, sync_record)
                sync_record.status = outcome_status
                sync_record.error_message = message if outcome_status != SyncStatus.PROCESSED else ''
                sync_record.processed_at = timezone.now()
                sync_record.save()

                if outcome_status == SyncStatus.PROCESSED:
                    synced_count += 1
                elif outcome_status == SyncStatus.CONFLICT:
                    conflict_count += 1
                else:
                    rejected_count += 1

                results.append({
                    'event_id': str(sync_record.event_id),
                    'idempotency_key': idempotency_key,
                    'status': outcome_status,
                    'message': message,
                    'is_duplicate': False,
                })

            except Exception as ex:
                logger.exception(f'Error processing sync event {event_uuid}: {ex}')
                sync_record.status = SyncStatus.REJECTED
                sync_record.error_message = str(ex)
                sync_record.processed_at = timezone.now()
                sync_record.save()
                rejected_count += 1
                results.append({
                    'event_id': str(sync_record.event_id),
                    'idempotency_key': idempotency_key,
                    'status': SyncStatus.REJECTED,
                    'error': str(ex),
                })

        # Record audit event for the overall sync operation
        WarehouseAuditEvent.objects.create(
            event_type=AuditEventType.SYNC_COMPLETED,
            actor=operator,
            summary=f'Synced {synced_count} offline events ({duplicate_count} dup, {conflict_count} conflict)',
            details={
                'device_id': device_id,
                'total_received': len(events),
                'synced': synced_count,
                'duplicates': duplicate_count,
                'conflicts': conflict_count,
                'rejected': rejected_count,
            },
        )

        return {
            'total_received': len(events),
            'synced_count': synced_count,
            'duplicate_count': duplicate_count,
            'conflict_count': conflict_count,
            'rejected_count': rejected_count,
            'results': results,
            'synced_at': timezone.now().isoformat(),
        }

    @classmethod
    def _handle_pick_completed(
        cls, payload: Dict[str, Any], operator, sync_record: SyncEvent
    ) -> Tuple[str, str]:
        """Process offline pick completion event."""
        task_id = payload.get('task_id')
        qty = Decimal(str(payload.get('picked_quantity', payload.get('quantity', 0))))
        scanned_barcode = payload.get('scanned_barcode', '')

        task = WarehouseTask.objects.filter(task_id=task_id).select_for_update().first()
        if not task:
            return SyncStatus.REJECTED, f'Task {task_id} not found.'

        # Conflict check: If already completed by another operator
        if task.status == WarehouseTaskStatus.COMPLETED:
            if task.assigned_operator_id and operator and task.assigned_operator_id != operator.id:
                return (
                    SyncStatus.CONFLICT,
                    f'Task {task_id} was already completed by {task.assigned_operator.username}.',
                )
            # Same operator repeating: accept idempotently
            return SyncStatus.PROCESSED, f'Task {task_id} was already completed.'

        # If task was cancelled
        if task.status == WarehouseTaskStatus.CANCELLED:
            return SyncStatus.CONFLICT, f'Task {task_id} was cancelled on the server.'

        # Execute confirmation and inventory adjustment
        task.confirm_pick(qty, scanned_barcode=scanned_barcode, user=operator)
        return SyncStatus.PROCESSED, f'Task {task_id} pick synced successfully ({qty} units).'

    @classmethod
    def _handle_task_started(
        cls, payload: Dict[str, Any], operator, sync_record: SyncEvent
    ) -> Tuple[str, str]:
        """Process offline task start event."""
        task_id = payload.get('task_id')
        task = WarehouseTask.objects.filter(task_id=task_id).first()
        if not task:
            return SyncStatus.REJECTED, f'Task {task_id} not found.'

        if task.status in [WarehouseTaskStatus.PENDING, WarehouseTaskStatus.ASSIGNED]:
            task.start(operator=operator, save=True)
            return SyncStatus.PROCESSED, f'Task {task_id} started.'

        return SyncStatus.PROCESSED, f'Task {task_id} already in status {task.status}.'

    @classmethod
    def _handle_exception_reported(
        cls, payload: Dict[str, Any], operator, sync_record: SyncEvent
    ) -> Tuple[str, str]:
        """Process offline exception ticket."""
        task_id = payload.get('task_id')
        ex_type = payload.get('exception_type', ExceptionType.SHORT_PICK)
        desc = payload.get('description', 'Reported while offline')
        rep_qty = payload.get('reported_quantity')

        task = WarehouseTask.objects.filter(task_id=task_id).first() if task_id else None
        if task and task.status != WarehouseTaskStatus.EXCEPTION:
            task.report_exception(ex_type, desc, reported_qty=rep_qty, user=operator)
        else:
            WarehouseException.objects.create(
                task=task,
                operator=operator,
                exception_type=ex_type,
                description=desc,
                reported_quantity=Decimal(str(rep_qty)) if rep_qty is not None else None,
            )

        return SyncStatus.PROCESSED, f'Exception {ex_type} recorded from offline queue.'
