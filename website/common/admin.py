import inspect
import logging

from django.contrib import admin
from django.db import models as django_models

logger = logging.getLogger(__name__)


def register_models_to_admin(models_module, module_base):
    for name, obj in inspect.getmembers(models_module, inspect.isclass):
        if (
            issubclass(obj, django_models.Model)
            and obj.__module__.split(".")[0] == module_base
        ):
            logger.debug(
                "Registering model '%s' from module '%s' in admin", name, module_base
            )
            admin.site.register(obj)
