from datetime import datetime, timedelta

from common.fields import Slot
from django.test import TestCase

from .models import EventWithSchedule


class EventWithVolunteersModelTests(TestCase):

    def test_should_create_slots_list(self):
        event = EventWithSchedule(
            name="toto",
            start_date=datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            end_date=datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
            slot_duration_schedule=timedelta(minutes=30),
            slot_duration_volunteer=timedelta(hours=2),
        )

        slots = event.schedule_slots()

        self.assertListEqual(
            slots,
            [
                Slot(
                    datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T08:30:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T08:30:00+02:00"),
                    datetime.fromisoformat("2025-06-01T09:00:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T09:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T09:30:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T09:30:00+02:00"),
                    datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
                ),
            ],
        )
