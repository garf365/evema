import logging

from common.fields import Slot
from django.db import models
from django.utils.timezone import now
from django_extensions.db.fields import AutoSlugField

logger = logging.getLogger(__name__)


class Event(models.Model):
    name = models.CharField(max_length=200, null=False)

    slug = AutoSlugField(populate_from="name")

    start_date = models.DateTimeField(null=False)
    end_date = models.DateTimeField(null=False)

    def __str__(self):
        return self.name


class RoleCategory(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=False)
    name = models.CharField(max_length=200, null=False)

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=200, null=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=False)
    occurence = models.IntegerField(null=False, default=1)
    order = models.IntegerField(null=False, default=1)
    weight = models.IntegerField(null=False, default=1)

    category = models.ForeignKey(
        RoleCategory, null=True, on_delete=models.SET_NULL, blank=True
    )

    start_date = models.DateTimeField(null=False, default=now)
    end_date = models.DateTimeField(null=False, default=now)

    with_validation_email = models.BooleanField(null=False, default=True)

    def __str__(self):
        return self.name

    @property
    def slot(self):
        return Slot(self.start_date, self.end_date)

    @property
    def slots_for_event(self):
        return [
            slot
            for slot in self.event.schedule_slots()
            if slot.is_contained_by(self.slot)
        ]
