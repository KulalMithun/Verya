"""Django AppConfig for OpenWES."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OpenWesConfig(AppConfig):
    """Configuration for Open Warehouse Execution System (OpenWES)."""

    name = 'openwes'
    verbose_name = _('Open Warehouse Execution System')

    def ready(self):
        """Perform initialization when the OpenWES app is loaded."""
        pass
