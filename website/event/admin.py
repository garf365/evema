import logging

from common.admin import register_models_to_admin

from . import models

logger = logging.getLogger(__name__)


register_models_to_admin(models, __name__.split(".")[0])
