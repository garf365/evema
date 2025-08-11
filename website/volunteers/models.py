import logging
from datetime import timedelta

from common.fields import Slot
from django.conf import settings
from django.db import models
from event.models import Event, RoleCategory
from phonenumber_field.modelfields import PhoneNumberField

logger = logging.getLogger(__name__)


class Volunteer(models.Model):
    firstname = models.CharField(max_length=200, null=False)
    lastname = models.CharField(max_length=200, null=False)
    email = models.CharField(max_length=200, null=False)

    phonenumber = PhoneNumberField(region="FR", max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.lastname} {self.firstname}"

    def __lt__(self, other):
        if not isinstance(other, Volunteer):
            return False

        if self.lastname < other.lastname:
            return True
        elif self.lastname == other.lastname and self.firstname < other.firstname:
            return True
        elif (
            self.lastname == other.lastname
            and self.firstname == other.firstname
            and self.id < other.id
        ):
            return True
        return False


def event_directory_path(instance, filename):
    return f"{settings.MEDIA_ROOT}/events/{instance.slug}/{filename}"


class EventWithVolunteers(Event):
    slot_duration_volunteer = models.DurationField(
        null=False, default=timedelta(minutes=30)
    )

    volunteers = models.ManyToManyField(
        Volunteer,
        through="VolunteerAvailability",
        through_fields=("event", "volunteer"),
    )

    convention = models.FileField(upload_to=event_directory_path, null=True, blank=True)

    def volunteer_slots(self):
        return Slot.create_slots(
            self.slot_duration_volunteer, self.start_date, self.end_date
        )

    def has_waiting_friendship(self):
        return VolunteerFriendshipWaiting.objects.filter(
            volunteeravailability__event=self
        ).exists()


class VolunteerAvailability(models.Model):
    event = models.ForeignKey(EventWithVolunteers, on_delete=models.CASCADE, null=False)
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, null=False)
    # TODO make any number of friends possible
    friend = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)

    maxslot = models.IntegerField(null=False, default=1)

    notes = models.TextField(null=True, blank=True)

    # TODO set default categories by config
    categories = models.ManyToManyField(RoleCategory)

    def is_available_at(self, from_, for_):
        return (
            len(
                self.volunteerslot_set.filter(
                    start_date__lte=from_, end_date__gte=(from_ + for_)
                )
            )
            == 1
        )

    @property
    def slots(self):
        return [av.slot for av in self.volunteerslot_set.all()]

    @property
    def slots_for_event(self):
        slots = self.slots
        return [
            slot
            for slot in self.event.schedule_slots()
            if any(slot.is_contained_by(s) for s in slots)
        ]

    def __lt__(self, other):
        if not isinstance(other, VolunteerAvailability):
            return False
        return self.volunteer < other.volunteer

    def __str__(self):
        return f"{str(self.volunteer)} - {str(self.event)}"


class VolunteerSlot(models.Model):
    availability = models.ForeignKey(
        VolunteerAvailability, on_delete=models.CASCADE, null=True, blank=True
    )
    start_date = models.DateTimeField(null=False)
    end_date = models.DateTimeField(null=False)

    @property
    def slot(self):
        return Slot(self.start_date, self.end_date)

    def __str__(self):
        return f"{str(self.availability)} - {self.start_date} - {self.end_date}"


class VolunteerFriendshipWaiting(models.Model):
    # TODO make any number of friends possible
    volunteeravailability = models.OneToOneField(
        VolunteerAvailability, on_delete=models.CASCADE, null=False
    )
    firstname = models.CharField(max_length=200, null=False)
    lastname = models.CharField(max_length=200, null=False)

    def __str__(self):
        return f"{self.lastname} {self.firstname}"
