from datetime import datetime, timedelta

from common.fields import Slot
from django.test import TestCase
from django.urls import reverse

from .models import (
    EventWithVolunteers,
    Volunteer,
    VolunteerAvailability,
    VolunteerFriendshipWaiting,
)


class RegisterVolunteer(TestCase):
    def setUp(self):
        self.event = EventWithVolunteers.objects.create(
            name="Name",
            start_date=datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            end_date=datetime.fromisoformat("2025-06-01T18:00:00+02:00"),
            slot_duration_volunteer=timedelta(hours=2),
        )

    def test_load_form(self):
        response = self.client.get(
            reverse("volunteers:register", kwargs={"slug": "name"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "volunteers/register.html")


class EventWithVolunteersModelTests(TestCase):

    def test_should_create_slots_list(self):
        event = EventWithVolunteers(
            name="toto",
            start_date=datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            end_date=datetime.fromisoformat("2025-06-01T18:00:00+02:00"),
            slot_duration_volunteer=timedelta(hours=2),
        )

        slots = event.volunteer_slots()

        self.assertListEqual(
            slots,
            [
                Slot(
                    datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T14:00:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T14:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T16:00:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T16:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T18:00:00+02:00"),
                ),
            ],
        )

    def test_should_rest_no_waiting_friendship(self):
        vol1 = Volunteer.objects.create(
            firstname="p1", lastname="n1", email="test@test.com"
        )

        vol2 = Volunteer.objects.create(
            firstname="p2", lastname="n2", email="test@test.com"
        )

        evt1 = EventWithVolunteers.objects.create(
            name="evt1",
            start_date=datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            end_date=datetime.fromisoformat("2025-06-01T18:00:00+02:00"),
            slot_duration_volunteer=timedelta(hours=2),
        )

        VolunteerAvailability.objects.create(event=evt1, volunteer=vol1)

        evt2 = EventWithVolunteers.objects.create(
            name="evt2",
            start_date=datetime.fromisoformat("2025-06-02T08:00:00+02:00"),
            end_date=datetime.fromisoformat("2025-06-02T18:00:00+02:00"),
            slot_duration_volunteer=timedelta(hours=2),
        )

        avl12 = VolunteerAvailability.objects.create(event=evt2, volunteer=vol1)
        avl22 = VolunteerAvailability.objects.create(event=evt2, volunteer=vol2)

        VolunteerFriendshipWaiting.objects.create(
            volunteeravailability=avl12, firstname="f1", lastname="l1"
        )
        VolunteerFriendshipWaiting.objects.create(
            volunteeravailability=avl22, firstname="f2", lastname="l2"
        )

        self.assertIs(evt1.has_waiting_friendship(), False)
        self.assertIs(evt2.has_waiting_friendship(), True)
