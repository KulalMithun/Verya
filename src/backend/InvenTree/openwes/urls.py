"""URL routing definitions for OpenWES REST API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from openwes.api import (
    AuditEventViewSet,
    OfflineSyncView,
    OperatorSessionViewSet,
    ReplenishmentTaskViewSet,
    VoiceCommandView,
    WarehouseAnalyticsView,
    WarehouseDashboardView,
    WarehouseExceptionViewSet,
    WarehouseLocationMetaViewSet,
    WarehouseTaskViewSet,
    WarehouseZoneViewSet,
)

router = DefaultRouter()
router.register('zones', WarehouseZoneViewSet, basename='openwes-zone')
router.register('locations', WarehouseLocationMetaViewSet, basename='openwes-location')
router.register('tasks', WarehouseTaskViewSet, basename='openwes-task')
router.register('exceptions', WarehouseExceptionViewSet, basename='openwes-exception')
router.register('replenishment', ReplenishmentTaskViewSet, basename='openwes-replenishment')
router.register('operators', OperatorSessionViewSet, basename='openwes-operator')
router.register('audit', AuditEventViewSet, basename='openwes-audit')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    # Dashboard KPI metrics
    path('dashboard/', WarehouseDashboardView.as_view(), name='openwes-dashboard'),
    # Voice command interaction
    path('voice/command/', VoiceCommandView.as_view(), name='openwes-voice-command'),
    # Offline-first sync
    path('sync/', OfflineSyncView.as_view(), name='openwes-sync'),
    # Analytics
    path('analytics/warehouse/', WarehouseAnalyticsView.as_view(), name='openwes-analytics-warehouse'),
]
