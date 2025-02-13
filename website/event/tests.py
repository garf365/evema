from django.test import TestCase

from .models import Event


class EventModelTests(TestCase):
    def test_should_str_return_name(self):
        event = Event(name="toto")
        self.assertEqual(str(event), "toto")
