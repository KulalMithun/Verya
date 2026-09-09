"""OpenWES Status Codes, Enums, and Constants."""

from django.utils.translation import gettext_lazy as _


class WarehouseTaskType:
    """Type of warehouse execution task."""

    PICK = 'PICK'
    PUTAWAY = 'PUTAWAY'
    REPLENISH = 'REPLENISH'
    COUNT = 'COUNT'
    RELOCATE = 'RELOCATE'

    CHOICES = [
        (PICK, _('Pick Item')),
        (PUTAWAY, _('Putaway Stock')),
        (REPLENISH, _('Replenish Bin')),
        (COUNT, _('Cycle Count')),
        (RELOCATE, _('Relocate Stock')),
    ]


class WarehouseTaskStatus:
    """Finite State Machine states for warehouse tasks."""

    PENDING = 'PENDING'
    ASSIGNED = 'ASSIGNED'
    IN_PROGRESS = 'IN_PROGRESS'
    PAUSED = 'PAUSED'
    COMPLETED = 'COMPLETED'
    PARTIAL = 'PARTIAL'
    EXCEPTION = 'EXCEPTION'
    CANCELLED = 'CANCELLED'

    CHOICES = [
        (PENDING, _('Pending Assignment')),
        (ASSIGNED, _('Assigned to Operator')),
        (IN_PROGRESS, _('In Progress')),
        (PAUSED, _('Paused')),
        (COMPLETED, _('Completed')),
        (PARTIAL, _('Partially Completed')),
        (EXCEPTION, _('Blocked by Exception')),
        (CANCELLED, _('Cancelled')),
    ]

    # Valid transitions map
    VALID_TRANSITIONS = {
        PENDING: [ASSIGNED, CANCELLED],
        ASSIGNED: [IN_PROGRESS, PENDING, CANCELLED],
        IN_PROGRESS: [COMPLETED, PARTIAL, PAUSED, EXCEPTION, CANCELLED],
        PAUSED: [IN_PROGRESS, CANCELLED, EXCEPTION],
        EXCEPTION: [IN_PROGRESS, PARTIAL, CANCELLED, COMPLETED],
        PARTIAL: [IN_PROGRESS, COMPLETED, CANCELLED],
        COMPLETED: [],
        CANCELLED: [],
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if transition from one status to another is permitted."""
        return to_status in cls.VALID_TRANSITIONS.get(from_status, [])


class WarehouseTaskPriority:
    """Priority levels for warehouse tasks."""

    LOW = 10
    MEDIUM = 20
    HIGH = 30
    CRITICAL = 40

    CHOICES = [
        (LOW, _('Low Priority')),
        (MEDIUM, _('Medium Priority')),
        (HIGH, _('High Priority')),
        (CRITICAL, _('Critical Priority')),
    ]


class ExceptionType:
    """Standardized warehouse exceptions."""

    SHORT_PICK = 'SHORT_PICK'
    DAMAGED_ITEM = 'DAMAGED_ITEM'
    MISSING_ITEM = 'MISSING_ITEM'
    BLOCKED_LOCATION = 'BLOCKED_LOCATION'
    WRONG_ITEM = 'WRONG_ITEM'
    WRONG_QUANTITY = 'WRONG_QUANTITY'
    STOCK_MISMATCH = 'STOCK_MISMATCH'
    NETWORK_FAILURE = 'NETWORK_FAILURE'

    CHOICES = [
        (SHORT_PICK, _('Short Pick (Insufficient Stock)')),
        (DAMAGED_ITEM, _('Damaged Item Found')),
        (MISSING_ITEM, _('Missing Item in Bin')),
        (BLOCKED_LOCATION, _('Blocked Location / Aisle')),
        (WRONG_ITEM, _('Wrong Item / Barcode Mismatch')),
        (WRONG_QUANTITY, _('Wrong Quantity Recorded')),
        (STOCK_MISMATCH, _('System vs Physical Mismatch')),
        (NETWORK_FAILURE, _('Network / Sync Failure')),
    ]


class ExceptionStatus:
    """Status lifecycle for an exception ticket."""

    REPORTED = 'REPORTED'
    INVESTIGATING = 'INVESTIGATING'
    RESOLVED = 'RESOLVED'
    REOPENED = 'REOPENED'

    CHOICES = [
        (REPORTED, _('Reported')),
        (INVESTIGATING, _('Under Investigation')),
        (RESOLVED, _('Resolved')),
        (REOPENED, _('Reopened')),
    ]


class OperatorStatus:
    """Current live status of a warehouse operator session."""

    ONLINE = 'ONLINE'
    OFFLINE = 'OFFLINE'
    PICKING = 'PICKING'
    IDLE = 'IDLE'
    BREAK = 'BREAK'
    BLOCKED = 'BLOCKED'

    CHOICES = [
        (ONLINE, _('Online')),
        (OFFLINE, _('Offline')),
        (PICKING, _('Picking')),
        (IDLE, _('Idle / Waiting')),
        (BREAK, _('On Break')),
        (BLOCKED, _('Blocked on Exception')),
    ]


class SyncStatus:
    """Status of offline event synchronization."""

    RECEIVED = 'RECEIVED'
    PROCESSED = 'PROCESSED'
    CONFLICT = 'CONFLICT'
    REJECTED = 'REJECTED'

    CHOICES = [
        (RECEIVED, _('Received')),
        (PROCESSED, _('Processed Successfully')),
        (CONFLICT, _('Conflict Detected')),
        (REJECTED, _('Rejected / Validation Error')),
    ]


class AuditEventType:
    """Auditable warehouse domain events."""

    TASK_CREATED = 'TASK_CREATED'
    TASK_ASSIGNED = 'TASK_ASSIGNED'
    TASK_STARTED = 'TASK_STARTED'
    TASK_PAUSED = 'TASK_PAUSED'
    TASK_RESUMED = 'TASK_RESUMED'
    ITEM_SCANNED = 'ITEM_SCANNED'
    QUANTITY_CONFIRMED = 'QUANTITY_CONFIRMED'
    SHORT_PICK_REPORTED = 'SHORT_PICK_REPORTED'
    ITEM_DAMAGED = 'ITEM_DAMAGED'
    TASK_COMPLETED = 'TASK_COMPLETED'
    INVENTORY_ADJUSTED = 'INVENTORY_ADJUSTED'
    SYNC_COMPLETED = 'SYNC_COMPLETED'
    REPLENISHMENT_GENERATED = 'REPLENISHMENT_GENERATED'
    EXCEPTION_REPORTED = 'EXCEPTION_REPORTED'
    EXCEPTION_RESOLVED = 'EXCEPTION_RESOLVED'

    CHOICES = [
        (TASK_CREATED, _('Task Created')),
        (TASK_ASSIGNED, _('Task Assigned')),
        (TASK_STARTED, _('Task Started')),
        (TASK_PAUSED, _('Task Paused')),
        (TASK_RESUMED, _('Task Resumed')),
        (ITEM_SCANNED, _('Item Barcode Scanned')),
        (QUANTITY_CONFIRMED, _('Quantity Confirmed')),
        (SHORT_PICK_REPORTED, _('Short Pick Reported')),
        (ITEM_DAMAGED, _('Damaged Item Reported')),
        (TASK_COMPLETED, _('Task Completed')),
        (INVENTORY_ADJUSTED, _('Inventory Adjusted')),
        (SYNC_COMPLETED, _('Offline Sync Completed')),
        (REPLENISHMENT_GENERATED, _('Replenishment Task Generated')),
        (EXCEPTION_REPORTED, _('Exception Reported')),
        (EXCEPTION_RESOLVED, _('Exception Resolved')),
    ]
