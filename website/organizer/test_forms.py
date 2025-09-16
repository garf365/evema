from django.test import TestCase
from model_bakery import baker

from .forms import RoleAndSlotBasedHiddenFormSet, ScheduleEventHiddenFormSet


class ScheduleEventHiddentFormSetTests(TestCase):
    def test_should_volunteer_not_required(self):
        schedule = baker.make("organizer.EventSchedule")
        roles = baker.make(
            "organizer.RoleWithSchedule", event=schedule.event, _quantity=3
        )
        volunteers = baker.make(
            "volunteers.VolunteerAvailability", event=schedule.event, _quantity=4
        )
        slots = baker.make(
            "organizer.EventScheduleSlot", schedule=schedule, _quantity=9
        )

        formset = ScheduleEventHiddenFormSet(instance=schedule)

        self.assertIsInstance(formset, RoleAndSlotBasedHiddenFormSet)
        for form in formset.forms:
            self.assertFalse(form.fields["volunteer"].required)


class RoleAndSlotBaseHiddenFormSetTests(TestCase):
    def setUp(self):
        self.schedule = baker.make("organizer.EventSchedule")
        self.roles = baker.make(
            "organizer.RoleWithSchedule",
            event=self.schedule.event,
            occurence=2,
            _quantity=3,
        )
        self.volunteers = baker.make(
            "volunteers.VolunteerAvailability", event=self.schedule.event, _quantity=4
        )
        self.slots = [
            baker.make(
                "organizer.EventScheduleSlot",
                schedule=self.schedule,
                role=self.roles[0],
                position=0,
            ),
            baker.make(
                "organizer.EventScheduleSlot",
                schedule=self.schedule,
                role=self.roles[0],
                position=1,
            ),
            baker.make(
                "organizer.EventScheduleSlot",
                schedule=self.schedule,
                role=self.roles[1],
                position=0,
            ),
            baker.make(
                "organizer.EventScheduleSlot",
                schedule=self.schedule,
                role=self.roles[1],
                position=1,
            ),
        ]

        self.formset = ScheduleEventHiddenFormSet(instance=self.schedule)

    def test_should_check_contain_index(self):
        self.assertTrue(0 in self.formset)
        self.assertTrue(((self.roles[0], 0), self.slots[0].slot) in self.formset)

        self.assertFalse(((self.roles[0], 2), self.slots[0].slot) in self.formset)
        self.assertFalse(
            ((baker.prepare("organizer.RoleWithSchedule"), 0), self.slots[0].slot)
            in self.formset
        )
        self.assertFalse(
            ((self.roles[0], 0), baker.prepare("organizer.EventScheduleSlot").slot)
            in self.formset
        )

    def test_should_return_element_at_index(self):
        form = self.formset[((self.roles[0], 0), self.slots[0].slot)]

        self.assertEqual(form, self.formset.forms[0])
        self.assertEqual(self.formset[0], self.formset.forms[0])

    def test_should_raise_index_error_if_not_found(self):
        with self.assertRaises(IndexError):
            self.formset[((self.roles[0], 2), self.slots[0].slot)]
