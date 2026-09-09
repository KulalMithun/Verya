"""Django Rest Framework Serializers for OpenWES."""

from rest_framework import serializers
from django.contrib.auth import get_user_model

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

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class WarehouseZoneSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    location_count = serializers.IntegerField(source='locations.count', read_only=True)

    class Meta:
        model = WarehouseZone
        fields = [
            'id',
            'code',
            'name',
            'description',
            'warehouse',
            'warehouse_name',
            'picking_strategy',
            'priority',
            'location_count',
        ]


class WarehouseLocationMetaSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    zone_code = serializers.CharField(source='zone.code', read_only=True)
    formatted_code = serializers.CharField(read_only=True)

    class Meta:
        model = WarehouseLocationMeta
        fields = [
            'id',
            'location',
            'location_name',
            'zone',
            'zone_code',
            'aisle',
            'bay',
            'level',
            'position',
            'coord_x',
            'coord_y',
            'coord_z',
            'is_pick_face',
            'is_reserve',
            'is_blocked',
            'block_reason',
            'formatted_code',
        ]


class WarehouseTaskSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source='part.name', read_only=True)
    part_ipn = serializers.CharField(source='part.IPN', read_only=True)
    part_description = serializers.CharField(source='part.description', read_only=True)
    part_units = serializers.CharField(source='part.units', read_only=True)
    source_location_name = serializers.CharField(source='source_location.name', read_only=True)
    dest_location_name = serializers.CharField(source='destination_location.name', read_only=True)
    operator_name = serializers.CharField(source='assigned_operator.username', read_only=True)
    order_reference = serializers.CharField(source='order.reference', read_only=True)

    class Meta:
        model = WarehouseTask
        fields = [
            'id',
            'task_id',
            'task_type',
            'status',
            'priority',
            'sequence',
            'order',
            'order_reference',
            'order_line',
            'part',
            'part_name',
            'part_ipn',
            'part_description',
            'part_units',
            'source_location',
            'source_location_name',
            'destination_location',
            'dest_location_name',
            'stock_item',
            'expected_quantity',
            'picked_quantity',
            'assigned_operator',
            'operator_name',
            'created_at',
            'started_at',
            'completed_at',
            'updated_at',
            'idempotency_key',
            'notes',
            'metadata',
        ]


class TaskAssignmentSerializer(serializers.ModelSerializer):
    operator_username = serializers.CharField(source='operator.username', read_only=True)
    task_identifier = serializers.CharField(source='task.task_id', read_only=True)

    class Meta:
        model = TaskAssignment
        fields = [
            'id',
            'task',
            'task_identifier',
            'operator',
            'operator_username',
            'score',
            'distance_score',
            'workload_score',
            'priority_score',
            'zone_score',
            'reason',
            'assigned_at',
        ]


class WarehouseExceptionSerializer(serializers.ModelSerializer):
    task_id_str = serializers.CharField(source='task.task_id', read_only=True)
    operator_name = serializers.CharField(source='operator.username', read_only=True)
    resolver_name = serializers.CharField(source='resolved_by.username', read_only=True)
    part_name = serializers.CharField(source='part.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = WarehouseException
        fields = [
            'id',
            'exception_id',
            'task',
            'task_id_str',
            'operator',
            'operator_name',
            'exception_type',
            'status',
            'description',
            'location',
            'location_name',
            'part',
            'part_name',
            'expected_quantity',
            'reported_quantity',
            'resolution',
            'resolved_by',
            'resolver_name',
            'created_at',
            'resolved_at',
        ]


class ReplenishmentTaskSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source='part.name', read_only=True)
    source_location_name = serializers.CharField(source='source_location.name', read_only=True)
    target_location_name = serializers.CharField(source='target_location.name', read_only=True)
    operator_name = serializers.CharField(source='assigned_operator.username', read_only=True)

    class Meta:
        model = ReplenishmentTask
        fields = [
            'id',
            'replenishment_id',
            'part',
            'part_name',
            'source_location',
            'source_location_name',
            'target_location',
            'target_location_name',
            'quantity_required',
            'quantity_replenished',
            'priority',
            'status',
            'assigned_operator',
            'operator_name',
            'created_at',
            'completed_at',
        ]


class OperatorSessionSerializer(serializers.ModelSerializer):
    operator_username = serializers.CharField(source='operator.username', read_only=True)
    zone_code = serializers.CharField(source='current_zone.code', read_only=True)
    current_task_id = serializers.CharField(source='current_task.task_id', read_only=True)

    class Meta:
        model = OperatorSession
        fields = [
            'id',
            'operator',
            'operator_username',
            'device_id',
            'status',
            'current_zone',
            'zone_code',
            'current_task',
            'current_task_id',
            'last_heartbeat',
            'ip_address',
            'battery_level',
            'app_version',
        ]


class SyncEventSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.username', read_only=True)

    class Meta:
        model = SyncEvent
        fields = [
            'id',
            'event_id',
            'idempotency_key',
            'operator',
            'operator_name',
            'device_id',
            'event_type',
            'payload',
            'status',
            'error_message',
            'received_at',
            'processed_at',
        ]


class WarehouseAuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.username', read_only=True)
    task_id_str = serializers.CharField(source='task.task_id', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    part_name = serializers.CharField(source='part.name', read_only=True)

    class Meta:
        model = WarehouseAuditEvent
        fields = [
            'id',
            'event_type',
            'actor',
            'actor_name',
            'task',
            'task_id_str',
            'location',
            'location_name',
            'part',
            'part_name',
            'summary',
            'details',
            'timestamp',
        ]
