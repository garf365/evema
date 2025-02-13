import logging
from datetime import timedelta

from common.fields import Slot
from django.db import models
from django.db.models import Count, Q
from django.utils.timezone import now
from event.models import Role
from volunteers.models import EventWithVolunteers, VolunteerAvailability

logger = logging.getLogger(__name__)


class EventWithSchedule(EventWithVolunteers):

    slot_duration_schedule = models.DurationField(
        null=False, default=timedelta(minutes=30)
    )

    def has_schedule_validated(self):
        return self.eventschedule_set.filter(validated_at__isnull=False).count() > 0

    def schedule_slots(self):
        return Slot.create_slots(
            self.slot_duration_schedule, self.start_date, self.end_date
        )


class EventSchedule(models.Model):
    class ScheduleType(models.TextChoices):
        GENERATED = "G", "generated"
        USER = "U", "user"
        BASE = "B", "base"
        EMPTY = "E", "empty"

    event = models.ForeignKey(EventWithSchedule, on_delete=models.CASCADE, null=False)
    name = models.CharField(max_length=200, null=False, default="", blank=True)
    saved_at = models.DateTimeField(default=now, null=False)
    based_on = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )
    type = models.CharField(
        max_length=3, choices=ScheduleType.choices, default=ScheduleType.USER
    )
    deletable = models.BooleanField(default=True, null=False)
    validated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.name:
            return f"{self.name} - {str(self.event)} - {self.id}"
        else:
            return f"{self.saved_at} - {str(self.event)} - {self.id}"

    def can_delete(self):
        return self.validated_at is None and self.deletable

    def get_missing_by_slots(self):
        return {
            Slot(r["start_date"], r["end_date"]): r["total"]
            for r in self.eventscheduleslot_set.filter(
                Q(role__isnull=True) | Q(volunteer__isnull=True)
            )
            .values("start_date", "end_date")
            .annotate(total=Count("start_date"))
            .order_by("start_date")
        }

    def get_schedule_by_roles(self):
        slots = (
            self.eventscheduleslot_set.prefetch_related(
                "role", "volunteer", "volunteer__volunteer"
            )
            .filter(role__isnull=False)
            .order_by("start_date")
        )

        schedule = {(slot.role.order, slot.position, slot.role): {} for slot in slots}
        for slot in slots:
            schedule[(slot.role.order, slot.position, slot.role)][slot.slot] = {
                "volunteer": slot.volunteer
            }

        schedule = dict(
            sorted([(k, dict(sorted(v.items()))) for k, v in schedule.items()])
        )

        for role, volunteers in schedule.items():
            slots = [k for k in volunteers.keys()]

            while slots:
                slot = slots.pop(0)
                grouped = [slot]
                nb = 1
                while slots and volunteers[slot] == volunteers[slots[0]]:
                    grouped.append(slots.pop(0))
                    nb += 1
                for s in grouped:
                    volunteers[s]["nb"] = nb
                    volunteers[s]["first"] = slot

        return schedule

    # TODO simplify, too complex
    def get_schedule_by_volunteers(self):
        slots = (
            self.eventscheduleslot_set.prefetch_related(
                "role", "volunteer", "volunteer__volunteer"
            )
            .filter(role__isnull=False, volunteer__isnull=False)
            .order_by("start_date")
        )

        volunteers = self.event.volunteeravailability_set.all()
        schedule = {volunteer: {} for volunteer in volunteers}
        for slot in slots:
            schedule[slot.volunteer][slot.slot] = {
                "role": slot.role,
                "position": slot.position,
                "available": True,
            }

        for volunteer in volunteers:
            volunteer_slots = volunteer.volunteerslot_set.all()
            for slot in self.event.schedule_slots():
                if any([slot.is_contained_by(vs.slot) for vs in volunteer_slots]):
                    try:
                        schedule[volunteer][slot]["availability"] = True
                    except KeyError:
                        schedule[volunteer][slot] = {"availability": True}

        schedule = dict(
            sorted([(k, dict(sorted(v.items()))) for k, v in schedule.items()])
        )

        for volunteer, roles in schedule.items():
            slots = [k for k in roles.keys()]

            while slots:
                slot = slots.pop(0)
                grouped = [slot]
                nb = 1
                while (
                    slots
                    and roles[slot] == roles[slots[0]]
                    and slots[0].start == grouped[-1].end
                ):
                    grouped.append(slots.pop(0))
                    nb += 1
                for s in grouped:
                    roles[s]["nb"] = nb
                    roles[s]["first"] = slot

        return schedule


class EventScheduleSlot(models.Model):
    schedule = models.ForeignKey(EventSchedule, on_delete=models.CASCADE, null=False)
    volunteer = models.ForeignKey(
        VolunteerAvailability, on_delete=models.SET_NULL, null=True, blank=True
    )
    start_date = models.DateTimeField(null=False)
    end_date = models.DateTimeField(null=False)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.IntegerField(null=False, default=0)
    fixed = models.BooleanField(default=False)

    @property
    def slot(self):
        return Slot(self.start_date, self.end_date)

    def __str__(self):
        return (
            f"{str(self.schedule)} - "
            f"{self.volunteer.volunteer if self.volunteer else ""} - "
            f"{self.start_date}"
        )


class ScheduleEventRemainder(models.Model):
    event = models.ForeignKey(EventWithSchedule, on_delete=models.CASCADE, null=False)
    days_before = models.IntegerField(null=False, default=15)
    done_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        s = f"{str(self.event)} - {self.days_before}"
        if self.done_at is not None:
            s += " - done"
        return s
