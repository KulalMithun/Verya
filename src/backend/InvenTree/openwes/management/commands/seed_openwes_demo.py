"""Management command to generate rich, realistic demo data for OpenWES.

Creates:
- Mangalore Demo Warehouse
- 4 Zones (A, B, C, D)
- 40+ coordinate-mapped Bin Locations (A-01-01 to D-05-04)
- 30+ Parts across diverse categories with barcodes
- 100+ StockItems with realistic stock levels
- 20+ Sales Orders
- 10 Operators with active sessions
- 50+ Warehouse Tasks (Pending, Assigned, In Progress, Completed)
- Warehouse Exceptions, Replenishment Tasks, and Audit Logs
"""

import random
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from company.models import Company
from openwes.models import (
    OperatorSession,
    ReplenishmentTask,
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
    WarehouseTaskPriority,
    WarehouseTaskStatus,
    WarehouseTaskType,
)
from order.models import SalesOrder, SalesOrderLineItem
from part.models import Part, PartCategory
from stock.models import StockItem, StockLocation

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds realistic warehouse execution data for OpenWES demo'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting OpenWES Demo Data Seeding...'))

        # 1. Create Main Warehouse Location
        warehouse, _ = StockLocation.objects.get_or_create(
            name='Mangalore Central Logistics Hub',
            defaults={
                'description': 'Primary automated fulfillment and distribution center',
            },
        )

        # 2. Create 4 Warehouse Zones
        zone_configs = [
            ('ZONE-A', 'Zone A - Electronics & Microchips', 'S_SHAPE', 10),
            ('ZONE-B', 'Zone B - Fast Moving Consumables', 'S_SHAPE', 20),
            ('ZONE-C', 'Zone C - Industrial & Mechanical', 'NEAREST_NEIGHBOR', 30),
            ('ZONE-D', 'Zone D - Reserve High-Bay Pallets', 'STRICT_ZONAL', 40),
        ]
        zones = {}
        for code, name, strat, prio in zone_configs:
            z, _ = WarehouseZone.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'warehouse': warehouse,
                    'picking_strategy': strat,
                    'priority': prio,
                },
            )
            zones[code] = z

        self.stdout.write(f'Created {len(zones)} Warehouse Zones.')

        # 3. Create 40+ coordinate-mapped Bin Locations
        created_locations = []
        zone_keys = list(zones.keys())

        for z_idx, z_code in enumerate(zone_keys):
            zone_obj = zones[z_code]
            aisle_char = chr(ord('A') + z_idx)
            is_reserve_zone = (z_code == 'ZONE-D')

            for aisle in range(1, 4):
                for bay in range(1, 5):
                    loc_name = f'{aisle_char}-{aisle:02d}-{bay:02d}'
                    loc, _ = StockLocation.objects.get_or_create(
                        name=loc_name,
                        parent=warehouse,
                        defaults={
                            'description': f'{zone_obj.name} Aisle {aisle}, Bay {bay}',
                        },
                    )
                    created_locations.append(loc)

                    # Compute coordinates
                    # X: Zone offset + Aisle spacing
                    x = (z_idx * 40.0) + (aisle * 4.0)
                    y = bay * 2.5
                    z = 1.0 if not is_reserve_zone else 4.0

                    WarehouseLocationMeta.objects.update_or_create(
                        location=loc,
                        defaults={
                            'zone': zone_obj,
                            'aisle': f'{aisle_char}{aisle}',
                            'bay': f'{bay:02d}',
                            'level': '01',
                            'position': '01',
                            'coord_x': x,
                            'coord_y': y,
                            'coord_z': z,
                            'is_pick_face': not is_reserve_zone,
                            'is_reserve': is_reserve_zone,
                            'is_blocked': (loc_name == 'A-02-04'),  # 1 blocked location demo
                            'block_reason': 'Conveyor maintenance' if loc_name == 'A-02-04' else '',
                        },
                    )

        self.stdout.write(f'Created {len(created_locations)} coordinate-mapped bin locations.')

        # 4. Create Part Categories and 30+ Parts
        cat_e, _ = PartCategory.objects.get_or_create(name='Electronics', defaults={'description': 'ICs and Sensors'})
        cat_c, _ = PartCategory.objects.get_or_create(name='Consumables', defaults={'description': 'Packaging & Fasteners'})
        cat_m, _ = PartCategory.objects.get_or_create(name='Mechanical', defaults={'description': 'Motors and Bearings'})

        products_data = [
            ('ESP32-S3-WROOM', 'ESP32-S3 Wi-Fi/BLE MCU Module', cat_e, 'units', 'BAR-ESP32-001'),
            ('STM32F405RGT6', 'ARM Cortex-M4 168MHz MCU', cat_e, 'units', 'BAR-STM32-002'),
            ('RP2040-MCU', 'Dual Cortex-M0+ Microcontroller', cat_e, 'units', 'BAR-RP20-003'),
            ('BME280-SENSOR', 'Digital Humidity Pressure Sensor', cat_e, 'units', 'BAR-BME2-004'),
            ('MPU-6050-IMU', '6-Axis Gyroscope & Accelerometer', cat_e, 'units', 'BAR-MPU6-005'),
            ('NRF52840-BLE', 'Bluetooth 5.0 SoC Module', cat_e, 'units', 'BAR-NRF5-006'),
            ('L7805CV-VREG', '5V Positive Voltage Regulator', cat_e, 'units', 'BAR-L780-007'),
            ('AMS1117-3.3', '3.3V 1A LDO Voltage Regulator', cat_e, 'units', 'BAR-AMS1-008'),
            ('OLED-096-I2C', '0.96 inch 128x64 OLED Display', cat_e, 'units', 'BAR-OLED-009'),
            ('NEO-6M-GPS', 'High Sensitivity GPS Module', cat_e, 'units', 'BAR-NEO6-010'),
            ('M3-HEX-SCREW-10', 'M3 x 10mm Stainless Cap Screws (Pack 50)', cat_c, 'packs', 'BAR-M3SC-011'),
            ('M4-LOCK-NUT', 'M4 Nylon Insert Lock Nut (Pack 100)', cat_c, 'packs', 'BAR-M4NT-012'),
            ('HEATSHRINK-KIT', 'Polyolefin Heat Shrink Tube Assortment', cat_c, 'kits', 'BAR-HSHR-013'),
            ('ZIP-TIES-150', 'Nylon Cable Ties 150mm Black (Pack 100)', cat_c, 'packs', 'BAR-ZTIE-014'),
            ('ESD-BUBBLE-ROLL', 'Anti-Static Bubble Wrap Roll 50m', cat_c, 'rolls', 'BAR-ESDB-015'),
            ('KAPTON-TAPE-20', 'High Temp Polyimide Kapton Tape 20mm', cat_c, 'rolls', 'BAR-KAPT-016'),
            ('SILICA-GEL-5G', 'Silica Gel Desiccant Packets 5g (Pack 50)', cat_c, 'packs', 'BAR-SGEL-017'),
            ('CORRUGATED-BX-S', 'Heavy Duty Shipping Box 20x15x10cm', cat_c, 'units', 'BAR-BOXS-018'),
            ('CORRUGATED-BX-M', 'Heavy Duty Shipping Box 30x20x15cm', cat_c, 'units', 'BAR-BOXM-019'),
            ('PACKING-TAPE-CL', 'Clear Acrylic Carton Sealing Tape 48mm', cat_c, 'rolls', 'BAR-PTAP-020'),
            ('NEMA17-STEPPER', 'NEMA 17 Stepper Motor 1.5A 42Ncm', cat_m, 'units', 'BAR-NEMA-021'),
            ('NEMA23-STEPPER', 'NEMA 23 High Torque Stepper Motor 2.8A', cat_m, 'units', 'BAR-NM23-022'),
            ('MG996R-SERVO', 'Metal Gear High Torque Digital Servo', cat_m, 'units', 'BAR-MG99-023'),
            ('BALL-BEAR-608ZZ', 'Precision Skate Ball Bearing 608ZZ (Pack 10)', cat_m, 'packs', 'BAR-608Z-024'),
            ('LINEAR-BEAR-LM8UU', 'Linear Motion Ball Bearing LM8UU', cat_m, 'units', 'BAR-LM8U-025'),
            ('GT2-TIMING-BELT', 'GT2 6mm Neoprene Timing Belt 5m', cat_m, 'meters', 'BAR-GT2B-026'),
            ('GT2-PULLEY-20T', 'Aluminum Timing Pulley 20 Teeth 5mm Bore', cat_m, 'units', 'BAR-GT2P-027'),
            ('LEADSCREW-T8-300', 'T8 8mm Lead Screw 300mm with Brass Nut', cat_m, 'units', 'BAR-T8LS-028'),
            ('ALU-EXTR-2020', '2020 T-Slot Aluminum Extrusion 1000mm', cat_m, 'units', 'BAR-2020-029'),
            ('COOLING-FAN-4010', '12V 4010 Brushless Axial Cooling Fan', cat_m, 'units', 'BAR-FAN4-030'),
            ('DRV8825-DRIVER', 'Stepper Motor Driver Module with Heat Sink', cat_e, 'units', 'BAR-DRV8-031'),
            ('XT60-CONNECTOR', 'XT60 High Current Male/Female Pair (Pack 5)', cat_c, 'packs', 'BAR-XT60-032'),
        ]

        parts_list = []
        for ipn, name, cat, units, barcode in products_data:
            p, _ = Part.objects.get_or_create(
                name=name,
                defaults={
                    'IPN': ipn,
                    'description': f'Industrial warehouse inventory SKU {ipn} [{barcode}]',
                    'category': cat,
                    'active': True,
                    'salable': True,
                },
            )
            parts_list.append(p)

        self.stdout.write(f'Created {len(parts_list)} Parts/SKUs.')

        # 5. Populate StockItems (100+ records)
        stock_items = []
        for p in parts_list:
            # Distribute stock across forward pick faces and reserve locations
            pick_loc = random.choice(created_locations[:30])
            reserve_loc = random.choice(created_locations[30:])

            # Pick Face item
            si_pick, _ = StockItem.objects.get_or_create(
                part=p,
                location=pick_loc,
                defaults={
                    'quantity': Decimal(random.randint(15, 80)),
                    'batch': f'B-{random.randint(100, 999)}',
                },
            )
            stock_items.append(si_pick)

            # Reserve item
            si_res, _ = StockItem.objects.get_or_create(
                part=p,
                location=reserve_loc,
                defaults={
                    'quantity': Decimal(random.randint(100, 500)),
                    'batch': f'B-RES-{random.randint(100, 999)}',
                },
            )
            stock_items.append(si_res)

        self.stdout.write(f'Created {len(stock_items)} Stock Item inventory records.')

        # 6. Create Customer & Sales Orders
        customer, _ = Company.objects.get_or_create(
            name='Global Tech Logistics Ltd',
            defaults={'is_customer': True, 'description': 'Primary fulfillment client'},
        )

        orders = []
        for i in range(1, 21):
            ref = f'SO-{202600 + i}'
            order, _ = SalesOrder.objects.get_or_create(
                reference=ref,
                defaults={
                    'customer': customer,
                    'description': f'Fulfillment Batch #{i} for customer dispatch',
                },
            )
            orders.append(order)

        self.stdout.write(f'Created {len(orders)} Sales Orders.')

        # 0. Ensure Admin Superuser Exists
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'System',
                'last_name': 'Administrator',
                'email': 'admin@openwes.local',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        admin_user.set_password('inventree')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        # 7. Create 10 Warehouse Operators
        operator_names = [
            ('op_rajesh', 'Rajesh', 'Kumar'),
            ('op_vikram', 'Vikram', 'Shetty'),
            ('op_anita', 'Anita', 'Rao'),
            ('op_sunil', 'Sunil', 'Verma'),
            ('op_priya', 'Priya', 'Nair'),
            ('op_arjun', 'Arjun', 'Patel'),
            ('op_kavita', 'Kavita', 'Singh'),
            ('op_manoj', 'Manoj', 'Deshmukh'),
            ('op_deepa', 'Deepa', 'Iyer'),
            ('op_rahul', 'Rahul', 'Gupta'),
        ]

        operators = []
        statuses = [
            OperatorStatus.PICKING,
            OperatorStatus.PICKING,
            OperatorStatus.ONLINE,
            OperatorStatus.ONLINE,
            OperatorStatus.IDLE,
            OperatorStatus.IDLE,
            OperatorStatus.BREAK,
            OperatorStatus.OFFLINE,
            OperatorStatus.PICKING,
            OperatorStatus.BLOCKED,
        ]

        zone_list = list(zones.values())
        for idx, (uname, fname, lname) in enumerate(operator_names):
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'email': f'{uname}@openwes.local',
                    'is_staff': True,
                },
            )
            user.set_password('openwes2026')
            user.is_staff = True
            user.is_active = True
            user.save()
            operators.append(user)

            OperatorSession.objects.update_or_create(
                operator=user,
                defaults={
                    'device_id': f'TC57-ZBR-{100 + idx}',
                    'status': statuses[idx % len(statuses)],
                    'current_zone': zone_list[idx % len(zone_list)],
                    'last_heartbeat': timezone.now(),
                    'battery_level': random.randint(45, 98),
                    'app_version': 'OpenWES-v1.0.4',
                },
            )

        self.stdout.write(f'Created {len(operators)} Operator sessions.')

        # 8. Create 50+ Warehouse Tasks in realistic states
        task_statuses = [
            WarehouseTaskStatus.COMPLETED,
            WarehouseTaskStatus.COMPLETED,
            WarehouseTaskStatus.COMPLETED,
            WarehouseTaskStatus.IN_PROGRESS,
            WarehouseTaskStatus.ASSIGNED,
            WarehouseTaskStatus.PENDING,
            WarehouseTaskStatus.PENDING,
            WarehouseTaskStatus.EXCEPTION,
        ]

        created_tasks = []
        now = timezone.now()

        for idx in range(1, 55):
            part = parts_list[(idx - 1) % len(parts_list)]
            order = orders[(idx - 1) % len(orders)]
            assigned_op = operators[(idx - 1) % len(operators)]
            t_status = task_statuses[idx % len(task_statuses)]
            pick_loc = created_locations[(idx - 1) % 30]

            exp_qty = Decimal(random.randint(1, 8))
            picked_qty = exp_qty if t_status == WarehouseTaskStatus.COMPLETED else Decimal('0.0')
            if t_status == WarehouseTaskStatus.IN_PROGRESS:
                picked_qty = Decimal(random.randint(0, int(exp_qty) - 1))

            started_at = now - timezone.timedelta(minutes=random.randint(10, 180)) if t_status != WarehouseTaskStatus.PENDING else None
            completed_at = now - timezone.timedelta(minutes=random.randint(1, 60)) if t_status == WarehouseTaskStatus.COMPLETED else None

            task_id = f'WES-2026-{idx:04d}'
            task, _ = WarehouseTask.objects.update_or_create(
                task_id=task_id,
                defaults={
                    'task_type': WarehouseTaskType.PICK,
                    'status': t_status,
                    'priority': random.choice([WarehouseTaskPriority.LOW, WarehouseTaskPriority.MEDIUM, WarehouseTaskPriority.HIGH, WarehouseTaskPriority.CRITICAL]),
                    'sequence': idx,
                    'order': order,
                    'part': part,
                    'source_location': pick_loc,
                    'expected_quantity': exp_qty,
                    'picked_quantity': picked_qty,
                    'assigned_operator': assigned_op if t_status != WarehouseTaskStatus.PENDING else None,
                    'started_at': started_at,
                    'completed_at': completed_at,
                },
            )
            created_tasks.append(task)

            # Record assignment score breakdown for assigned tasks
            if task.assigned_operator:
                TaskAssignment.objects.update_or_create(
                    task=task,
                    defaults={
                        'operator': task.assigned_operator,
                        'score': round(random.uniform(12.0, 45.0), 2),
                        'distance_score': round(random.uniform(5.0, 20.0), 2),
                        'workload_score': round(random.uniform(0.0, 25.0), 2),
                        'priority_score': round(random.uniform(10.0, 30.0), 2),
                        'zone_score': 0.0,
                        'reason': 'Operator active in matching aisle; queue load balanced.',
                    },
                )

        self.stdout.write(f'Created {len(created_tasks)} Warehouse Tasks.')

        # 9. Create Warehouse Exceptions
        ex_configs = [
            (created_tasks[7], operators[0], ExceptionType.SHORT_PICK, 'Only 2 units available in bin instead of 5 expected.', Decimal('2.0'), Decimal('5.0')),
            (created_tasks[15], operators[2], ExceptionType.DAMAGED_ITEM, 'Packaging crushed on OLED display during pick.', Decimal('1.0'), Decimal('1.0')),
            (created_tasks[23], operators[4], ExceptionType.BLOCKED_LOCATION, 'Aisle A2 blocked by pallet jack.', None, None),
            (created_tasks[31], operators[6], ExceptionType.WRONG_ITEM, 'Barcode scanned does not match SKU.', Decimal('0.0'), Decimal('2.0')),
            (created_tasks[39], operators[8], ExceptionType.MISSING_ITEM, 'Bin A-01-03 empty upon arrival.', Decimal('0.0'), Decimal('4.0')),
        ]

        for task_obj, op, ex_t, desc, rep_qty, exp_qty in ex_configs:
            ex_obj, _ = WarehouseException.objects.update_or_create(
                exception_id=f'EX-{task_obj.task_id[-4:]}',
                defaults={
                    'task': task_obj,
                    'operator': op,
                    'exception_type': ex_t,
                    'status': ExceptionStatus.REPORTED,
                    'description': desc,
                    'location': task_obj.source_location,
                    'part': task_obj.part,
                    'reported_quantity': rep_qty,
                    'expected_quantity': exp_qty,
                },
            )

        # 10. Create Replenishment Tasks
        for i in range(1, 9):
            part_r = parts_list[i % len(parts_list)]
            rep_id = f'REP-2026-{i:03d}'
            ReplenishmentTask.objects.update_or_create(
                replenishment_id=rep_id,
                defaults={
                    'part': part_r,
                    'source_location': created_locations[32 + (i % 6)],
                    'target_location': created_locations[i % 20],
                    'quantity_required': Decimal(random.randint(20, 60)),
                    'quantity_replenished': Decimal('0.0'),
                    'priority': 30,
                    'status': WarehouseTaskStatus.PENDING,
                },
            )

        # 11. Record Initial Audit Events
        for task in created_tasks[:10]:
            WarehouseAuditEvent.objects.create(
                event_type=AuditEventType.TASK_CREATED,
                actor=operators[0],
                task=task,
                location=task.source_location,
                part=task.part,
                summary=f'Task {task.task_id} generated for {task.part.name}',
                details={'expected_qty': float(task.expected_quantity)},
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded OpenWES Demo Data!'))
