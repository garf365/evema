from django.test import TestCase
from datetime import datetime

from .models import Event, RoleCategory, Role

from common.fields import Slot


class EventModelTests(TestCase):
    def test_should_str_return_name(self):
        event = Event(name="toto")
        self.assertEqual(str(event), "toto")


class RoleCategoryTests(TestCase):
    def test_should_str_return_name(self):
        event = Event(name="toto")
        category = RoleCategory(event=event, name="titi")
        self.assertEqual(str(category), "titi")


class RoleTests(TestCase):
    def setUp(self):
        event = Event(name="toto", start_date=datetime.fromiso)
        category = RoleCategory(event=event, name="titi")
        self.role = Role(
            name="tata",
            event=event,
            occurence=2,
            order=1,
            weight=8,
            category=category,
            start_date=datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            end_date=datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
            with_validation_email=True,
        )

    def test_should_str_return_name(self):
        self.assertEqual(str(self.role), "tata")

    def test_should_return_slot(self):
        self.assertEqual(
            self.role.slot,
            Slot(
                datetime.fromisoformat("2025-06-01T06:00:00+00:00"),
                datetime.fromisoformat("2025-06-01T08:00:00+00:00"),
            ),
        )
