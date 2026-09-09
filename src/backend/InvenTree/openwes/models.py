"""Database models for OpenWES (Open Warehouse Execution System)."""

import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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


class WarehouseZone(models.Model):
    """Warehouse picking zone or operational area."""

    code = models.CharField(
        max_length=32,
        unique=True,
        verbose_name=_('Zone Code'),
        help_text=_('Unique identifier e.g. ZONE-A, AISLE-1'),
    )
    name = models.CharField(max_length=100, verbose_name=_('Zone Name'))
    description = models.CharField(max_length=250, blank=True, verbose_name=_('Description'))
    warehouse = models.ForeignKey(
        'stock.StockLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_zones',
        verbose_name=_('Warehouse Location'),
    )
    picking_strategy = models.CharField(
        max_length=32,
        default='S_SHAPE',
        choices=[
            ('S_SHAPE', _('S-Shape / Snake Routing')),
            ('NEAREST_NEIGHBOR', _('Nearest-Neighbor TSP')),
            ('STRICT_ZONAL', _('Strict Zonal Ordering')),
        ],
        verbose_name=_('Default Picking Strategy'),
    )
    priority = models.IntegerField(default=10, verbose_name=_('Priority'))

    class Meta:
        verbose_name = _('Warehouse Zone')
        verbose_name_plural = _('Warehouse Zones')
        ordering = ['priority', 'code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class WarehouseLocationMeta(models.Model):
    """Coordinate metadata and physical characteristics for a StockLocation."""

    location = models.OneToOneField(
        'stock.StockLocation',
        on_delete=models.CASCADE,
        related_name='openwes_meta',
        verbose_name=_('Stock Location'),
    )
    zone = models.ForeignKey(
        WarehouseZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locations',
        verbose_name=_('Zone'),
    )
    aisle = models.CharField(max_length=16, blank=True, verbose_name=_('Aisle'))
    bay = models.CharField(max_length=16, blank=True, verbose_name=_('Bay / Rack'))
    level = models.CharField(max_length=16, blank=True, verbose_name=_('Shelf Level'))
    position = models.CharField(max_length=16, blank=True, verbose_name=_('Bin Position'))

    # Spatial coordinates for pick-path optimization
    coord_x = models.FloatField(default=0.0, verbose_name=_('X Coordinate (Meters)'))
    coord_y = models.FloatField(default=0.0, verbose_name=_('Y Coordinate (Meters)'))
    coord_z = models.FloatField(default=0.0, verbose_name=_('Z Coordinate (Meters)'))

    is_pick_face = models.BooleanField(default=True, verbose_name=_('Is Pick Face'))
    is_reserve = models.BooleanField(default=False, verbose_name=_('Is Reserve Storage'))
    is_blocked = models.BooleanField(default=False, verbose_name=_('Is Blocked'))
    block_reason = models.CharField(max_length=255, blank=True, verbose_name=_('Block Reason'))

    class Meta:
        verbose_name = _('Warehouse Location Meta')
        verbose_name_plural = _('Warehouse Location Metas')

    def __str__(self):
        return f'{self.location.name} ({self.formatted_code})'

    @property
    def formatted_code(self):
        """Standard warehouse bin code like A-01-02-01."""
        parts = [p for p in [self.aisle, self.bay, self.level, self.position] if p]
        return '-'.join(parts) if parts else self.location.name


def generate_task_id():
    """Generate sequential or unique task identifier."""
    return f'WES-{uuid.uuid4().hex[:8].upper()}'


class WarehouseTask(models.Model):
    """Core warehouse execution task (Pick, Putaway, Replenishment, Cycle Count)."""

    task_id = models.CharField(
        max_length=64,
        unique=True,
        default=generate_task_id,
        db_index=True,
        verbose_name=_('Task ID'),
    )
    task_type = models.CharField(
        max_length=32,
        choices=WarehouseTaskType.CHOICES,
        default=WarehouseTaskType.PICK,
        db_index=True,
        verbose_name=_('Task Type'),
    )
    status = models.CharField(
        max_length=32,
        choices=WarehouseTaskStatus.CHOICES,
        default=WarehouseTaskStatus.PENDING,
        db_index=True,
        verbose_name=_('Status'),
    )
    priority = models.IntegerField(
        choices=WarehouseTaskPriority.CHOICES,
        default=WarehouseTaskPriority.MEDIUM,
        db_index=True,
        verbose_name=_('Priority'),
    )
    sequence = models.IntegerField(default=0, verbose_name=_('Route Sequence'))

    # Associated order references
    order = models.ForeignKey(
        'order.SalesOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_tasks',
        verbose_name=_('Sales Order'),
    )
    order_line = models.ForeignKey(
        'order.SalesOrderLineItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_tasks',
        verbose_name=_('Order Line Item'),
    )

    # Inventory objects
    part = models.ForeignKey(
        'part.Part',
        on_delete=models.CASCADE,
        related_name='openwes_tasks',
        verbose_name=_('Part / SKU'),
    )
    source_location = models.ForeignKey(
        'stock.StockLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_source_tasks',
        verbose_name=_('Source Location'),
    )
    destination_location = models.ForeignKey(
        'stock.StockLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_dest_tasks',
        verbose_name=_('Destination Location'),
    )
    stock_item = models.ForeignKey(
        'stock.StockItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_tasks',
        verbose_name=_('Stock Item'),
    )

    expected_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('1.0'),
        verbose_name=_('Expected Quantity'),
    )
    picked_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=Decimal('0.0'),
        verbose_name=_('Picked Quantity'),
    )

    assigned_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_assigned_tasks',
        verbose_name=_('Assigned Operator'),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Started At'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Completed At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    idempotency_key = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_('Idempotency Key'),
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_('Metadata'))

    class Meta:
        verbose_name = _('Warehouse Task')
        verbose_name_plural = _('Warehouse Tasks')
        ordering = ['sequence', '-priority', 'created_at']

    def __str__(self):
        return f'{self.task_id} [{self.task_type}] {self.part.name} ({self.status})'

    def transition_to(self, new_status: str, save: bool = True):
        """Validate and apply status transition."""
        if not WarehouseTaskStatus.can_transition(self.status, new_status):
            raise ValidationError(
                _(f'Invalid task transition from {self.status} to {new_status}')
            )
        self.status = new_status
        if new_status == WarehouseTaskStatus.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        elif new_status == WarehouseTaskStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        if save:
            self.save()

    def assign(self, operator, save: bool = True):
        """Assign task to a specific operator."""
        self.assigned_operator = operator
        if self.status == WarehouseTaskStatus.PENDING:
            self.transition_to(WarehouseTaskStatus.ASSIGNED, save=False)
        if save:
            self.save()

    def start(self, operator=None, save: bool = True):
        """Start task execution."""
        if operator and not self.assigned_operator:
            self.assigned_operator = operator
        self.transition_to(WarehouseTaskStatus.IN_PROGRESS, save=save)

    def pause(self, save: bool = True):
        """Pause active task."""
        self.transition_to(WarehouseTaskStatus.PAUSED, save=save)

    def resume(self, save: bool = True):
        """Resume paused task."""
        self.transition_to(WarehouseTaskStatus.IN_PROGRESS, save=save)

    @transaction.atomic
    def confirm_pick(self, quantity: Decimal, scanned_barcode: str = None, user=None):
        """Confirm picked quantity and adjust inventory."""
        if self.status not in [WarehouseTaskStatus.IN_PROGRESS, WarehouseTaskStatus.ASSIGNED]:
            if self.status == WarehouseTaskStatus.COMPLETED:
                return  # Idempotent no-op
            raise ValidationError(_(f'Task {self.task_id} is not in progress.'))

        quantity = Decimal(str(quantity))
        self.picked_quantity = quantity

        # If stock item is connected, adjust quantity
        if self.stock_item and quantity > 0:
            current_stock = self.stock_item.quantity
            new_stock = max(Decimal('0.0'), current_stock - quantity)
            self.stock_item.quantity = new_stock
            self.stock_item.save()

            # Record inventory audit event
            WarehouseAuditEvent.objects.create(
                event_type=AuditEventType.INVENTORY_ADJUSTED,
                actor=user or self.assigned_operator,
                task=self,
                location=self.source_location,
                part=self.part,
                summary=f'Deducted {quantity} {self.part.units or "units"} of {self.part.name}',
                details={
                    'stock_item_id': self.stock_item.id,
                    'previous_stock': float(current_stock),
                    'deducted': float(quantity),
                    'new_stock': float(new_stock),
                    'scanned_barcode': scanned_barcode,
                },
            )

        if self.picked_quantity >= self.expected_quantity:
            self.transition_to(WarehouseTaskStatus.COMPLETED, save=False)
        else:
            self.transition_to(WarehouseTaskStatus.PARTIAL, save=False)

        self.save()

        WarehouseAuditEvent.objects.create(
            event_type=AuditEventType.TASK_COMPLETED if self.status == WarehouseTaskStatus.COMPLETED else AuditEventType.QUANTITY_CONFIRMED,
            actor=user or self.assigned_operator,
            task=self,
            location=self.source_location,
            part=self.part,
            summary=f'Task {self.task_id} picked {self.picked_quantity}/{self.expected_quantity}',
            details={'status': self.status, 'picked_quantity': float(self.picked_quantity)},
        )

    def report_exception(self, exception_type: str, description: str, reported_qty=None, user=None):
        """Flag task with an exception ticket."""
        self.transition_to(WarehouseTaskStatus.EXCEPTION, save=True)
        ticket = WarehouseException.objects.create(
            task=self,
            operator=user or self.assigned_operator,
            exception_type=exception_type,
            description=description,
            location=self.source_location,
            part=self.part,
            expected_quantity=self.expected_quantity,
            reported_quantity=Decimal(str(reported_qty)) if reported_qty is not None else None,
        )
        WarehouseAuditEvent.objects.create(
            event_type=AuditEventType.EXCEPTION_REPORTED,
            actor=user or self.assigned_operator,
            task=self,
            location=self.source_location,
            part=self.part,
            summary=f'Exception {exception_type} on {self.task_id}: {description}',
            details={'exception_id': ticket.exception_id, 'exception_type': exception_type},
        )
        return ticket


class TaskAssignment(models.Model):
    """Explainable task allocation log from the assignment engine."""

    task = models.OneToOneField(
        WarehouseTask,
        on_delete=models.CASCADE,
        related_name='assignment_detail',
        verbose_name=_('Task'),
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='openwes_allocations',
        verbose_name=_('Operator'),
    )
    score = models.FloatField(verbose_name=_('Total Assignment Score'))
    distance_score = models.FloatField(default=0.0, verbose_name=_('Distance Score'))
    workload_score = models.FloatField(default=0.0, verbose_name=_('Workload Score'))
    priority_score = models.FloatField(default=0.0, verbose_name=_('Priority Score'))
    zone_score = models.FloatField(default=0.0, verbose_name=_('Zone Match Score'))
    reason = models.TextField(blank=True, verbose_name=_('Allocation Explanation / Reason'))
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Assigned At'))

    class Meta:
        verbose_name = _('Task Assignment')
        verbose_name_plural = _('Task Assignments')

    def __str__(self):
        return f'{self.task.task_id} -> {self.operator.username} (Score: {self.score:.2f})'


def generate_exception_id():
    return f'EX-{uuid.uuid4().hex[:6].upper()}'


class WarehouseException(models.Model):
    """Operational warehouse exception ticket."""

    exception_id = models.CharField(
        max_length=32,
        unique=True,
        default=generate_exception_id,
        db_index=True,
        verbose_name=_('Exception ID'),
    )
    task = models.ForeignKey(
        WarehouseTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exceptions',
        verbose_name=_('Warehouse Task'),
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_exceptions',
        verbose_name=_('Reporting Operator'),
    )
    exception_type = models.CharField(
        max_length=32,
        choices=ExceptionType.CHOICES,
        default=ExceptionType.SHORT_PICK,
        db_index=True,
        verbose_name=_('Exception Type'),
    )
    status = models.CharField(
        max_length=32,
        choices=ExceptionStatus.CHOICES,
        default=ExceptionStatus.REPORTED,
        db_index=True,
        verbose_name=_('Ticket Status'),
    )
    description = models.TextField(verbose_name=_('Problem Description'))
    location = models.ForeignKey(
        'stock.StockLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_exceptions',
        verbose_name=_('Location'),
    )
    part = models.ForeignKey(
        'part.Part',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_exceptions',
        verbose_name=_('Part'),
    )
    expected_quantity = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, verbose_name=_('Expected Qty')
    )
    reported_quantity = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, verbose_name=_('Reported Qty')
    )
    resolution = models.TextField(blank=True, verbose_name=_('Resolution Notes'))
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_exceptions',
        verbose_name=_('Resolved By (Supervisor)'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Reported At'))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Resolved At'))

    class Meta:
        verbose_name = _('Warehouse Exception')
        verbose_name_plural = _('Warehouse Exceptions')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.exception_id} [{self.exception_type}] ({self.status})'

    def resolve(self, resolver_user, resolution_notes: str = ''):
        """Supervisor resolution action."""
        self.status = ExceptionStatus.RESOLVED
        self.resolved_by = resolver_user
        self.resolution = resolution_notes
        self.resolved_at = timezone.now()
        self.save()

        # If task was waiting on this exception, allow task to resume
        if self.task and self.task.status == WarehouseTaskStatus.EXCEPTION:
            self.task.transition_to(WarehouseTaskStatus.IN_PROGRESS, save=True)

        WarehouseAuditEvent.objects.create(
            event_type=AuditEventType.EXCEPTION_RESOLVED,
            actor=resolver_user,
            task=self.task,
            location=self.location,
            part=self.part,
            summary=f'Exception {self.exception_id} resolved by {resolver_user.username}',
            details={'resolution': resolution_notes},
        )


def generate_replenish_id():
    return f'REP-{uuid.uuid4().hex[:6].upper()}'


class ReplenishmentTask(models.Model):
    """Movement from reserve bulk storage to active forward pick locations."""

    replenishment_id = models.CharField(
        max_length=32,
        unique=True,
        default=generate_replenish_id,
        db_index=True,
        verbose_name=_('Replenishment ID'),
    )
    part = models.ForeignKey(
        'part.Part',
        on_delete=models.CASCADE,
        related_name='replenishment_tasks',
        verbose_name=_('Part'),
    )
    source_location = models.ForeignKey(
        'stock.StockLocation',
        on_delete=models.CASCADE,
        related_name='replenishment_sources',
        verbose_name=_('Reserve Source Location'),
    )
    target_location = models.ForeignKey(
        'stock.StockLocation',
        on_delete=models.CASCADE,
        related_name='replenishment_targets',
        verbose_name=_('Target Pick Face Location'),
    )
    quantity_required = models.DecimalField(
        max_digits=15, decimal_places=4, verbose_name=_('Quantity Required')
    )
    quantity_replenished = models.DecimalField(
        max_digits=15, decimal_places=4, default=Decimal('0.0'), verbose_name=_('Replenished Qty')
    )
    priority = models.IntegerField(default=30, verbose_name=_('Priority'))
    status = models.CharField(
        max_length=32,
        choices=WarehouseTaskStatus.CHOICES,
        default=WarehouseTaskStatus.PENDING,
        verbose_name=_('Status'),
    )
    assigned_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_replenishments',
        verbose_name=_('Assigned Operator'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Completed At'))

    class Meta:
        verbose_name = _('Replenishment Task')
        verbose_name_plural = _('Replenishment Tasks')
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f'{self.replenishment_id}: {self.part.name} ({self.quantity_required} units)'


class OperatorSession(models.Model):
    """Real-time active terminal session for a warehouse operator."""

    operator = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='openwes_session',
        verbose_name=_('Operator'),
    )
    device_id = models.CharField(max_length=128, blank=True, verbose_name=_('Device / Terminal ID'))
    status = models.CharField(
        max_length=32,
        choices=OperatorStatus.CHOICES,
        default=OperatorStatus.ONLINE,
        verbose_name=_('Current Status'),
    )
    current_zone = models.ForeignKey(
        WarehouseZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_operators',
        verbose_name=_('Current Zone'),
    )
    current_task = models.ForeignKey(
        WarehouseTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_session',
        verbose_name=_('Active Task'),
    )
    last_heartbeat = models.DateTimeField(default=timezone.now, verbose_name=_('Last Heartbeat'))
    ip_address = models.CharField(max_length=64, blank=True, verbose_name=_('IP Address'))
    battery_level = models.IntegerField(null=True, blank=True, verbose_name=_('Battery %'))
    app_version = models.CharField(max_length=32, blank=True, verbose_name=_('App Version'))

    class Meta:
        verbose_name = _('Operator Session')
        verbose_name_plural = _('Operator Sessions')

    def __str__(self):
        return f'{self.operator.username} ({self.status})'

    def heartbeat(self, battery=None, zone=None, task=None):
        """Refresh heartbeat and operator state."""
        self.last_heartbeat = timezone.now()
        if battery is not None:
            self.battery_level = battery
        if zone:
            self.current_zone = zone
        if task is not None:
            self.current_task = task
        self.save()


class SyncEvent(models.Model):
    """Idempotent sync event journal for offline warehouse clients."""

    event_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        verbose_name=_('Event UUID'),
    )
    idempotency_key = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name=_('Client Idempotency Key'),
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_sync_events',
        verbose_name=_('Operator'),
    )
    device_id = models.CharField(max_length=128, blank=True, verbose_name=_('Device ID'))
    event_type = models.CharField(max_length=64, verbose_name=_('Event Type'))
    payload = models.JSONField(default=dict, verbose_name=_('Event Payload'))
    status = models.CharField(
        max_length=32,
        choices=SyncStatus.CHOICES,
        default=SyncStatus.RECEIVED,
        verbose_name=_('Sync Status'),
    )
    error_message = models.TextField(blank=True, verbose_name=_('Processing Error Message'))
    received_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Received At'))
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Processed At'))

    class Meta:
        verbose_name = _('Sync Event')
        verbose_name_plural = _('Sync Events')
        ordering = ['-received_at']

    def __str__(self):
        return f'{self.idempotency_key} [{self.event_type}] ({self.status})'


class WarehouseAuditEvent(models.Model):
    """Immutable audit trail for all critical warehouse events."""

    event_type = models.CharField(
        max_length=64,
        choices=AuditEventType.CHOICES,
        db_index=True,
        verbose_name=_('Event Type'),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_audit_events',
        verbose_name=_('Actor / User'),
    )
    task = models.ForeignKey(
        WarehouseTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events',
        verbose_name=_('Warehouse Task'),
    )
    location = models.ForeignKey(
        'stock.StockLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_audit_events',
        verbose_name=_('Location'),
    )
    part = models.ForeignKey(
        'part.Part',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='openwes_audit_events',
        verbose_name=_('Part'),
    )
    summary = models.CharField(max_length=255, verbose_name=_('Event Summary'))
    details = models.JSONField(default=dict, blank=True, verbose_name=_('Event Details'))
    timestamp = models.DateTimeField(default=timezone.now, db_index=True, verbose_name=_('Timestamp'))

    class Meta:
        verbose_name = _('Warehouse Audit Event')
        verbose_name_plural = _('Warehouse Audit Events')
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.username if self.actor else 'System'
        return f'{self.timestamp.strftime("%Y-%m-%d %H:%M:%S")} [{self.event_type}] {actor_name}: {self.summary}'
