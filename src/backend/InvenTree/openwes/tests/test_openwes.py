"""Comprehensive Test Suite for OpenWES (Open Warehouse Execution System)."""

import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APITestCase

from openwes.engines.assignment import TaskAssignmentEngine
from openwes.engines.routing import (
    NearestNeighborOptimizer,
    SShapeOptimizer,
    ZoneCoordinateOptimizer,
    optimize_pick_path,
)
from openwes.engines.sync import SyncEngine
from openwes.engines.voice import (
    VoiceCommandParser,
    VoiceCommandType,
    VoiceState,
    VoiceStateMachine,
)
from openwes.models import (
    OperatorSession,
    ReplenishmentTask,
    SyncEvent,
    TaskAssignment,
    WarehouseAuditEvent,
    WarehouseException,
    WarehouseLocationMeta,
    WarehouseTask,
    WarehouseZone,
)
from openwes.status_codes import (
    AuditEventType,
    ExceptionStatus,
    ExceptionType,
    OperatorStatus,
    SyncStatus,
    WarehouseTaskPriority,
    WarehouseTaskStatus,
    WarehouseTaskType,
)
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

User = get_user_model()


class OpenWESTestBase(TestCase):
    """Base test setup with standard warehouse entities."""

    def setUp(self):
        super().setUp()
        self.warehouse = StockLocation.objects.create(name='Test Logistics Depot')
        self.zone_a = WarehouseZone.objects.create(
            code='ZONE-A', name='Zone A Fast Pick', warehouse=self.warehouse
        )
        self.zone_b = WarehouseZone.objects.create(
            code='ZONE-B', name='Zone B Bulk', warehouse=self.warehouse
        )

        # Create two bin locations
        self.loc_a1 = StockLocation.objects.create(name='A-01-01', parent=self.warehouse)
        self.loc_a2 = StockLocation.objects.create(name='A-01-02', parent=self.warehouse)
        self.loc_b1 = StockLocation.objects.create(name='B-01-01', parent=self.warehouse)

        WarehouseLocationMeta.objects.create(
            location=self.loc_a1, zone=self.zone_a, aisle='A1', bay='01', coord_x=4.0, coord_y=2.5
        )
        WarehouseLocationMeta.objects.create(
            location=self.loc_a2, zone=self.zone_a, aisle='A1', bay='02', coord_x=4.0, coord_y=5.0
        )
        WarehouseLocationMeta.objects.create(
            location=self.loc_b1, zone=self.zone_b, aisle='B1', bay='01', coord_x=40.0, coord_y=2.5, is_reserve=True
        )

        # Part & Stock
        self.category = PartCategory.objects.create(name='Industrial Modules')
        self.part1 = Part.objects.create(
            name='Microcontroller Unit MCU-32',
            IPN='MCU-32',
            category=self.category,
        )
        self.stock1 = StockItem.objects.create(
            part=self.part1, location=self.loc_a1, quantity=Decimal('50.0'), batch='BATCH-001'
        )

        # Users / Operators
        self.operator1 = User.objects.create_user(username='op_tester1', password='password123')
        self.operator2 = User.objects.create_user(username='op_tester2', password='password123')
        self.supervisor = User.objects.create_user(username='supervisor_dan', password='password123', is_staff=True)

        self.session1 = OperatorSession.objects.create(
            operator=self.operator1, status=OperatorStatus.ONLINE, current_zone=self.zone_a
        )
        self.session2 = OperatorSession.objects.create(
            operator=self.operator2, status=OperatorStatus.ONLINE, current_zone=self.zone_b
        )


class TaskLifecycleAndStateMachineTest(OpenWESTestBase):
    """Test task execution lifecycle and strict state machine transitions."""

    def test_task_creation_and_defaults(self):
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            stock_item=self.stock1,
            expected_quantity=Decimal('5.0'),
        )
        self.assertEqual(task.status, WarehouseTaskStatus.PENDING)
        self.assertEqual(task.task_type, WarehouseTaskType.PICK)
        self.assertTrue(task.task_id.startswith('WES-'))

    def test_valid_state_transitions(self):
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            expected_quantity=Decimal('10.0'),
        )
        # PENDING -> ASSIGNED
        task.assign(self.operator1)
        self.assertEqual(task.status, WarehouseTaskStatus.ASSIGNED)
        self.assertEqual(task.assigned_operator, self.operator1)

        # ASSIGNED -> IN_PROGRESS
        task.start()
        self.assertEqual(task.status, WarehouseTaskStatus.IN_PROGRESS)
        self.assertIsNotNone(task.started_at)

        # IN_PROGRESS -> PAUSED -> IN_PROGRESS
        task.pause()
        self.assertEqual(task.status, WarehouseTaskStatus.PAUSED)
        task.resume()
        self.assertEqual(task.status, WarehouseTaskStatus.IN_PROGRESS)

    def test_invalid_state_transition_raises_validation_error(self):
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            status=WarehouseTaskStatus.COMPLETED,
        )
        # Cannot transition from COMPLETED to IN_PROGRESS
        with self.assertRaises(ValidationError):
            task.transition_to(WarehouseTaskStatus.IN_PROGRESS)


class BarcodeValidationAndInventoryAdjustmentTest(OpenWESTestBase):
    """Test barcode verification, inventory deduction, and audit logging."""

    def test_confirm_pick_deducts_inventory_and_logs_audit(self):
        initial_stock = self.stock1.quantity  # 50
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            stock_item=self.stock1,
            expected_quantity=Decimal('5.0'),
            status=WarehouseTaskStatus.IN_PROGRESS,
            assigned_operator=self.operator1,
        )

        task.confirm_pick(Decimal('5.0'), scanned_barcode='BAR-MCU-32', user=self.operator1)
        task.refresh_from_db()
        self.stock1.refresh_from_db()

        self.assertEqual(task.status, WarehouseTaskStatus.COMPLETED)
        self.assertEqual(task.picked_quantity, Decimal('5.0'))
        self.assertEqual(self.stock1.quantity, initial_stock - Decimal('5.0'))

        # Check audit event
        audit = WarehouseAuditEvent.objects.filter(task=task, event_type=AuditEventType.INVENTORY_ADJUSTED).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details['deducted'], 5.0)

    def test_partial_pick_transitions_to_partial(self):
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            stock_item=self.stock1,
            expected_quantity=Decimal('10.0'),
            status=WarehouseTaskStatus.IN_PROGRESS,
            assigned_operator=self.operator1,
        )
        task.confirm_pick(Decimal('6.0'), user=self.operator1)
        task.refresh_from_db()
        self.assertEqual(task.status, WarehouseTaskStatus.PARTIAL)
        self.assertEqual(task.picked_quantity, Decimal('6.0'))


class PickPathOptimizationEngineTest(TestCase):
    """Test deterministic warehouse routing algorithms."""

    def setUp(self):
        self.tasks = [
            {'task_id': 'T-01', 'location_name': 'A-01-05', 'coord_x': 3.0, 'coord_y': 7.5, 'coord_z': 1.0},
            {'task_id': 'T-02', 'location_name': 'A-01-01', 'coord_x': 3.0, 'coord_y': 1.5, 'coord_z': 1.0},
            {'task_id': 'T-03', 'location_name': 'A-02-04', 'coord_x': 6.0, 'coord_y': 6.0, 'coord_z': 1.0},
            {'task_id': 'T-04', 'location_name': 'A-02-01', 'coord_x': 6.0, 'coord_y': 1.5, 'coord_z': 1.0},
            {'task_id': 'T-05', 'location_name': 'B-01-02', 'coord_x': 40.0, 'coord_y': 3.0, 'coord_z': 1.0},
        ]

    def test_s_shape_optimizer_traversal(self):
        ordered, distance = optimize_pick_path(self.tasks, strategy='S_SHAPE')
        self.assertEqual(len(ordered), len(self.tasks))
        self.assertTrue(distance > 0)
        # Sequence numbers should be 1 to 5
        self.assertEqual([t['sequence'] for t in ordered], [1, 2, 3, 4, 5])

    def test_nearest_neighbor_optimizer(self):
        ordered, distance = optimize_pick_path(self.tasks, strategy='NEAREST_NEIGHBOR')
        self.assertEqual(len(ordered), len(self.tasks))
        self.assertTrue(distance > 0)

    def test_zonal_optimizer(self):
        ordered, distance = optimize_pick_path(self.tasks, strategy='ZONAL')
        self.assertEqual(len(ordered), len(self.tasks))


class TaskAssignmentEngineTest(OpenWESTestBase):
    """Test multi-criteria scoring and explainable allocation."""

    def test_assignment_scores_best_operator(self):
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,  # Zone A location
            expected_quantity=Decimal('2.0'),
            priority=WarehouseTaskPriority.HIGH,
        )
        engine = TaskAssignmentEngine()
        assignment = engine.assign_task(task, candidate_operators=[self.operator1, self.operator2])

        self.assertIsNotNone(assignment)
        task.refresh_from_db()
        self.assertEqual(task.status, WarehouseTaskStatus.ASSIGNED)
        # Operator 1 is active in Zone A (same zone as task), so should be favored over Operator 2 (in Zone B)
        self.assertEqual(task.assigned_operator, self.operator1)
        self.assertTrue(len(assignment.reason) > 0)

    def test_offline_operator_is_penalized(self):
        self.session1.status = OperatorStatus.OFFLINE
        self.session1.save()

        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            expected_quantity=Decimal('2.0'),
        )
        engine = TaskAssignmentEngine()
        assignment = engine.assign_task(task, candidate_operators=[self.operator1, self.operator2])
        self.assertEqual(assignment.operator, self.operator2)


class VoiceCommandParserAndFSMTest(OpenWESTestBase):
    """Test voice natural language parser and contextual FSM."""

    def test_parser_intents(self):
        # Pick numbers
        p1 = VoiceCommandParser.parse('pick 5 units')
        self.assertEqual(p1['command'], VoiceCommandType.CONFIRM_PICK)
        self.assertEqual(p1['quantity'], 5)

        p2 = VoiceCommandParser.parse('picked twelve')
        self.assertEqual(p2['command'], VoiceCommandType.CONFIRM_PICK)
        self.assertEqual(p2['quantity'], 12)

        # Short pick
        p3 = VoiceCommandParser.parse('only three are available')
        self.assertEqual(p3['command'], VoiceCommandType.SHORT_PICK)
        self.assertEqual(p3['quantity'], 3)

        # Exceptions
        p4 = VoiceCommandParser.parse('bin is blocked')
        self.assertEqual(p4['command'], VoiceCommandType.BLOCKED_LOCATION)

        p5 = VoiceCommandParser.parse('item is damaged and leaking')
        self.assertEqual(p5['command'], VoiceCommandType.DAMAGED)

    def test_voice_fsm_progression(self):
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            stock_item=self.stock1,
            expected_quantity=Decimal('5.0'),
            assigned_operator=self.operator1,
            status=WarehouseTaskStatus.ASSIGNED,
        )

        fsm = VoiceStateMachine(initial_state=VoiceState.IDLE, task=task)

        # IDLE -> say "ready" -> NAVIGATING
        res1 = fsm.process_utterance('ready', operator=self.operator1)
        self.assertEqual(res1['state'], VoiceState.NAVIGATING)
        self.assertIn('Proceed to location', res1['spoken_response'])

        # NAVIGATING -> say "arrived" -> AWAITING_ITEM_CONFIRMATION
        res2 = fsm.process_utterance('arrived', operator=self.operator1)
        self.assertEqual(res2['state'], VoiceState.AWAITING_ITEM_CONFIRMATION)

        # AWAITING_ITEM_CONFIRMATION -> say "confirm" -> AWAITING_QUANTITY
        res3 = fsm.process_utterance('confirm', operator=self.operator1)
        self.assertEqual(res3['state'], VoiceState.AWAITING_QUANTITY)

        # AWAITING_QUANTITY -> say "picked 5" -> COMPLETED
        res4 = fsm.process_utterance('picked 5', operator=self.operator1)
        self.assertEqual(res4['state'], VoiceState.COMPLETED)
        task.refresh_from_db()
        self.assertEqual(task.status, WarehouseTaskStatus.COMPLETED)


class OfflineSyncAndIdempotencyTest(OpenWESTestBase):
    """Test idempotent offline batch synchronization."""

    def test_idempotent_duplicate_events_do_not_double_deduct(self):
        initial_stock = self.stock1.quantity  # 50
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            stock_item=self.stock1,
            expected_quantity=Decimal('10.0'),
            status=WarehouseTaskStatus.IN_PROGRESS,
            assigned_operator=self.operator1,
        )

        event_id = uuid.uuid4()
        event = {
            'event_id': str(event_id),
            'idempotency_key': f'key-{event_id}',
            'event_type': 'PICK_COMPLETED',
            'payload': {
                'task_id': task.task_id,
                'picked_quantity': 10,
                'scanned_barcode': 'BAR-MCU-32',
            },
        }

        # First synchronization
        res1 = SyncEngine.process_sync_batch([event], operator=self.operator1)
        self.assertEqual(res1['synced_count'], 1)
        self.assertEqual(res1['duplicate_count'], 0)
        self.stock1.refresh_from_db()
        self.assertEqual(self.stock1.quantity, initial_stock - Decimal('10.0'))

        # Duplicate synchronization with same event_id
        res2 = SyncEngine.process_sync_batch([event], operator=self.operator1)
        self.assertEqual(res2['synced_count'], 0)
        self.assertEqual(res2['duplicate_count'], 1)

        # Verify stock was NOT deducted a second time
        self.stock1.refresh_from_db()
        self.assertEqual(self.stock1.quantity, initial_stock - Decimal('10.0'))

    def test_offline_sync_conflict_on_cancelled_task(self):
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            status=WarehouseTaskStatus.CANCELLED,
        )
        event = {
            'event_id': str(uuid.uuid4()),
            'idempotency_key': 'key-conflict-1',
            'event_type': 'PICK_COMPLETED',
            'payload': {'task_id': task.task_id, 'picked_quantity': 2},
        }
        res = SyncEngine.process_sync_batch([event], operator=self.operator1)
        self.assertEqual(res['conflict_count'], 1)


class ExceptionWorkflowAndReplenishmentTest(OpenWESTestBase):
    """Test exception ticket reporting, supervisor resolution, and replenishment."""

    def test_exception_lifecycle(self):
        task = WarehouseTask.objects.create(
            part=self.part1,
            source_location=self.loc_a1,
            expected_quantity=Decimal('5.0'),
            status=WarehouseTaskStatus.IN_PROGRESS,
            assigned_operator=self.operator1,
        )
        # Operator reports short pick
        ticket = task.report_exception(
            ExceptionType.SHORT_PICK, 'Only 2 items in bin', reported_qty=Decimal('2.0'), user=self.operator1
        )
        task.refresh_from_db()
        self.assertEqual(task.status, WarehouseTaskStatus.EXCEPTION)
        self.assertEqual(ticket.status, ExceptionStatus.REPORTED)

        # Supervisor resolves exception
        ticket.resolve(self.supervisor, resolution_notes='Investigated. Bin count updated.')
        ticket.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(ticket.status, ExceptionStatus.RESOLVED)
        self.assertEqual(task.status, WarehouseTaskStatus.IN_PROGRESS)

    def test_replenishment_task_creation(self):
        rep = ReplenishmentTask.objects.create(
            part=self.part1,
            source_location=self.loc_b1,
            target_location=self.loc_a1,
            quantity_required=Decimal('20.0'),
            priority=30,
        )
        self.assertTrue(rep.replenishment_id.startswith('REP-'))
        self.assertEqual(rep.status, WarehouseTaskStatus.PENDING)
