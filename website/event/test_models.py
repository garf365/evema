from datetime import datetime

from common.fields import Slot
from django.test import TestCase
from model_bakery import baker

from .models import Event, Role, RoleCategory


class EventModelTests(TestCase):
    def test_should_str_return_name(self):
        event = baker.make(Event, name="toto")
        self.assertEqual(str(event), "toto")


class RoleCategoryTests(TestCase):
    def test_should_str_return_name(self):
        category = baker.make(RoleCategory, name="titi")
        self.assertEqual(str(category), "titi")


class RoleTests(TestCase):
    def setUp(self):
        self.role = baker.make(
            Role,
            name="tata",
            start_date=datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            end_date=datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
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
