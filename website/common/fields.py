import logging
from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class Slot:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.start.isoformat() + "_" + self.end.isoformat()

    def __eq__(self, other):
        if not isinstance(other, Slot):
            return False
        return self.start == other.start and self.end == other.end

    def is_contained_by(self, other):
        if not isinstance(other, Slot):
            return False
        if self.start < other.start:
            return False
        if self.end > other.end:
            return False

        return True

    def __lt__(self, other):
        if self.start < other.start:
            return True
        elif self.start == other.start:
            return self.end < other.end
        return False

    def __hash__(self):
        return hash((self.start, self.end))

    @staticmethod
    def aggregate(slots):
        if not slots:
            return []

        result = []

        sorted_slots = sorted(slots)

        result.append(sorted_slots.pop(0))
        while sorted_slots:
            current = sorted_slots.pop(0)
            if current.start <= result[-1].end:
                result[-1].end = max(current.end, result[-1].end)
            else:
                result.append(current)

        return result

    @staticmethod
    def create_slots(duration, start_date, end_date):
        slot_values = []

        current = start_date

        while current < end_date:
            slot_values.append(Slot(current, current + duration))
            current += duration

        return slot_values


def str2slot(value):
    splitted = value.split("_")
    if len(splitted) != 2:
        raise ValidationError("Invalid slot", code="invalid")
    start = datetime.fromisoformat(splitted[0])
    end = datetime.fromisoformat(splitted[1])
    return Slot(start, end)


class SlotsField(forms.TypedMultipleChoiceField):
    widget = forms.CheckboxSelectMultiple

    def __init__(self, *args, **kwargs):
        super().__init__(coerce=str2slot, **kwargs)
