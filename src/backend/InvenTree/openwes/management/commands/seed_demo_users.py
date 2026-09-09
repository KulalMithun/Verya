"""Management command to seed ready-to-use demo user accounts for client evaluation.

Creates or updates:
- admin (admin123) - System Administrator (Superuser)
- manager (demo123) - Warehouse Operations Manager (Full Operations Staff)
- supervisor (demo123) - Shift Floor Supervisor (Supervision Staff)
- operator (demo123) - Handheld Scanner / Picker Operator (Execution Staff)
- demo (demo123) - Client Evaluation Demo Account (Viewer / Staff)
- op_rajesh, op_priya, op_deepa (demo123) - Floor Operators
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from users.models import RuleSet
from users.ruleset import RULESET_CHOICES

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates or updates standard demo accounts with pre-configured roles for client evaluation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-password',
            default='admin123',
            help='Password for admin user (default: admin123)',
        )
        parser.add_argument(
            '--demo-password',
            default='demo123',
            help='Password for demo / staff users (default: demo123)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        admin_pw = options['admin_password']
        demo_pw = options['demo_password']

        self.stdout.write(self.style.MIGRATE_HEADING('=== Veyra Demo User Account Seeder ==='))

        # 1. Setup Role Groups
        # Warehouse Managers Group (Full Operations)
        mgr_group, _ = Group.objects.get_or_create(name='Warehouse Managers')
        for r_name, _ in RULESET_CHOICES:
            rs, _ = RuleSet.objects.get_or_create(group=mgr_group, name=r_name)
            rs.can_view = True
            rs.can_add = True
            rs.can_change = True
            rs.can_delete = True
            rs.save()

        # Supervisors Group
        sup_group, _ = Group.objects.get_or_create(name='Warehouse Supervisors')
        for r_name, _ in RULESET_CHOICES:
            rs, _ = RuleSet.objects.get_or_create(group=sup_group, name=r_name)
            rs.can_view = True
            rs.can_add = True
            rs.can_change = True
            rs.can_delete = (r_name != 'admin')
            rs.save()

        # Floor Operators Group
        op_group, _ = Group.objects.get_or_create(name='Floor Operators')
        for r_name, _ in RULESET_CHOICES:
            rs, _ = RuleSet.objects.get_or_create(group=op_group, name=r_name)
            rs.can_view = True
            rs.can_add = (r_name in ['stock', 'part', 'build'])
            rs.can_change = (r_name in ['stock', 'part', 'build', 'sales_order', 'transfer_order'])
            rs.can_delete = False
            rs.save()

        # Read-Only / Demo Group
        demo_group, _ = Group.objects.get_or_create(name='Demo Viewers')
        for r_name, _ in RULESET_CHOICES:
            rs, _ = RuleSet.objects.get_or_create(group=demo_group, name=r_name)
            rs.can_view = True
            rs.can_add = False
            rs.can_change = False
            rs.can_delete = False
            rs.save()

        # 2. Define Demo Users Specification
        user_specs = [
            {
                'username': 'admin',
                'password': admin_pw,
                'email': 'admin@veyra.local',
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True,
                'groups': [mgr_group],
                'role_desc': 'Full System Superuser & Admin',
            },
            {
                'username': 'manager',
                'password': demo_pw,
                'email': 'manager@veyra.local',
                'first_name': 'Operations',
                'last_name': 'Manager',
                'is_staff': True,
                'is_superuser': False,
                'groups': [mgr_group],
                'role_desc': 'Warehouse Operations & Inventory Lead',
            },
            {
                'username': 'supervisor',
                'password': demo_pw,
                'email': 'supervisor@veyra.local',
                'first_name': 'Shift',
                'last_name': 'Supervisor',
                'is_staff': True,
                'is_superuser': False,
                'groups': [sup_group],
                'role_desc': 'Shift Supervisor (Wave & Task Dispatch)',
            },
            {
                'username': 'operator',
                'password': demo_pw,
                'email': 'operator@veyra.local',
                'first_name': 'Floor',
                'last_name': 'Picker',
                'is_staff': True,
                'is_superuser': False,
                'groups': [op_group],
                'role_desc': 'Zone A Handheld Scanner / HUD Operator',
            },
            {
                'username': 'demo',
                'password': demo_pw,
                'email': 'demo@veyra.local',
                'first_name': 'Client',
                'last_name': 'Demo User',
                'is_staff': True,
                'is_superuser': False,
                'groups': [demo_group],
                'role_desc': 'Client Evaluation Demo Account',
            },
            {
                'username': 'op_rajesh',
                'password': demo_pw,
                'email': 'rajesh@veyra.local',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'is_staff': True,
                'is_superuser': False,
                'groups': [op_group],
                'role_desc': 'Zone A Senior Picker',
            },
            {
                'username': 'op_priya',
                'password': demo_pw,
                'email': 'priya@veyra.local',
                'first_name': 'Priya',
                'last_name': 'Nair',
                'is_staff': True,
                'is_superuser': False,
                'groups': [op_group],
                'role_desc': 'Voice-Directed Picking Operator',
            },
            {
                'username': 'op_deepa',
                'password': demo_pw,
                'email': 'deepa@veyra.local',
                'first_name': 'Deepa',
                'last_name': 'Iyer',
                'is_staff': True,
                'is_superuser': False,
                'groups': [sup_group],
                'role_desc': 'Zone D Pallet Supervisor',
            },
        ]

        created_summary = []

        for spec in user_specs:
            uname = spec['username']
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'email': spec['email'],
                    'first_name': spec['first_name'],
                    'last_name': spec['last_name'],
                    'is_staff': spec['is_staff'],
                    'is_superuser': spec['is_superuser'],
                    'is_active': True,
                },
            )
            user.set_password(spec['password'])
            user.is_staff = spec['is_staff']
            user.is_superuser = spec['is_superuser']
            user.is_active = True
            user.first_name = spec['first_name']
            user.last_name = spec['last_name']
            user.email = spec['email']
            user.save()

            # Assign groups
            for grp in spec['groups']:
                user.groups.add(grp)

            # Ensure OperatorSession exists if openwes models are present
            try:
                from openwes.models import OperatorSession, WarehouseZone
                from openwes.status_codes import OperatorStatus

                first_zone = WarehouseZone.objects.first()
                OperatorSession.objects.update_or_create(
                    operator=user,
                    defaults={
                        'device_id': f'TC57-{uname.upper()[:8]}',
                        'status': OperatorStatus.ONLINE,
                        'current_zone': first_zone,
                        'last_heartbeat': timezone.now(),
                        'battery_level': 95,
                        'app_version': 'Veyra-v1.0.0',
                    },
                )
            except Exception:
                pass

            status_txt = 'Created' if created else 'Updated'
            created_summary.append((uname, spec['password'], spec['role_desc'], status_txt))

        # 3. Print Formatted Table
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('======================================================================'))
        self.stdout.write(self.style.SUCCESS('           VEYRA CLIENT DEMO USERS READY FOR EVALUATION              '))
        self.stdout.write(self.style.SUCCESS('======================================================================'))
        self.stdout.write(f'{"Username":<15} | {"Password":<12} | {"Role & Access":<40}')
        self.stdout.write('-' * 72)
        for uname, pwd, role, _ in created_summary:
            self.stdout.write(f'{uname:<15} | {pwd:<12} | {role:<40}')
        self.stdout.write(self.style.SUCCESS('======================================================================'))
        self.stdout.write(self.style.NOTICE('All accounts are active and ready for client demonstration.'))
        self.stdout.write('')
