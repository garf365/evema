from datetime import datetime, timedelta

from django.test import TestCase

from .fields import Slot, str2slot


class SlotTests(TestCase):
    def setUp(self):
        self.slot1 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )
        self.slot2 = Slot(
            datetime.fromisoformat("2025-06-01T06:00:00+00:00"),
            datetime.fromisoformat("2025-06-01T08:00:00+00:00"),
        )
        self.slot3 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+01:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )
        self.slot4 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+01:00"),
        )
        self.slot5 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+01:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+01:00"),
        )

    def test_should_compare_eq(self):
        self.assertIs(self.slot1 == self.slot2, True)
        self.assertIs(self.slot1 == self.slot3, False)
        self.assertIs(self.slot1 == self.slot4, False)
        self.assertIs(self.slot1 == self.slot5, False)

    def test___str__(self):
        self.assertEqual(
            str(self.slot1), "2025-06-01T08:00:00+02:00_2025-06-01T10:00:00+02:00"
        )

    def test_is_contained_by(self):
        slot1 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )

        slot2 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )
        slot3 = Slot(
            datetime.fromisoformat("2025-06-01T07:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )
        slot4 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
        )
        slot5 = Slot(
            datetime.fromisoformat("2025-06-01T07:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
        )

        slot6 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T09:00:00+02:00"),
        )
        slot7 = Slot(
            datetime.fromisoformat("2025-06-01T09:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )
        slot8 = Slot(
            datetime.fromisoformat("2025-06-01T08:30:00+02:00"),
            datetime.fromisoformat("2025-06-01T09:30:00+02:00"),
        )
        slot9 = Slot(
            datetime.fromisoformat("2025-06-01T09:30:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:30:00+02:00"),
        )

        self.assertEqual(slot1.is_contained_by(slot2), True)
        self.assertEqual(slot1.is_contained_by(slot3), True)
        self.assertEqual(slot1.is_contained_by(slot4), True)
        self.assertEqual(slot1.is_contained_by(slot5), True)

        self.assertEqual(slot1.is_contained_by(slot6), False)
        self.assertEqual(slot1.is_contained_by(slot7), False)
        self.assertEqual(slot1.is_contained_by(slot8), False)
        self.assertEqual(slot1.is_contained_by(slot9), False)

    def test_aggregate_simple(self):
        slot1 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T09:00:00+02:00"),
        )
        slot2 = Slot(
            datetime.fromisoformat("2025-06-01T09:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )
        slot3 = Slot(
            datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
        )

        result = Slot.aggregate([slot1, slot2, slot3])

        self.assertEqual(
            result,
            [
                Slot(
                    datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
                ),
            ],
        )

    def test_aggregate_overlap(self):
        slot1 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T09:00:00+02:00"),
        )
        slot2 = Slot(
            datetime.fromisoformat("2025-06-01T08:30:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )
        slot3 = Slot(
            datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
        )

        result = Slot.aggregate([slot1, slot2, slot3])

        self.assertEqual(
            result,
            [
                Slot(
                    datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
                ),
            ],
        )

    def test_aggregate_inside(self):
        slot1 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )
        slot2 = Slot(
            datetime.fromisoformat("2025-06-01T08:30:00+02:00"),
            datetime.fromisoformat("2025-06-01T09:00:00+02:00"),
        )
        slot3 = Slot(
            datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
        )

        result = Slot.aggregate([slot1, slot2, slot3])

        self.assertEqual(
            result,
            [
                Slot(
                    datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
                ),
            ],
        )

    def test_aggregate_bigger(self):
        slot1 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T09:00:00+02:00"),
        )
        slot2 = Slot(
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
        )
        slot3 = Slot(
            datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
        )

        result = Slot.aggregate([slot1, slot2, slot3])

        self.assertEqual(
            result,
            [
                Slot(
                    datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
                ),
                Slot(
                    datetime.fromisoformat("2025-06-01T11:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
                ),
            ],
        )

    def test_create_slots(self):
        slots = Slot.create_slots(
            timedelta(hours=2),
            datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
            datetime.fromisoformat("2025-06-01T18:00:00+02:00"),
        )

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


class Str2slotTests(TestCase):
    def test_func(self):
        for raw, expected in [
            (
                "2025-06-01T08:00:00+02:00_2025-06-01T10:00:00+02:00",
                Slot(
                    datetime.fromisoformat("2025-06-01T08:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
                ),
            ),
            (
                "2025-06-01T10:00:00+02:00_2025-06-01T12:00:00+02:00",
                Slot(
                    datetime.fromisoformat("2025-06-01T10:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T12:00:00+02:00"),
                ),
            ),
            (
                "2025-06-01T16:00:00+02:00_2025-06-01T18:00:00+02:00",
                Slot(
                    datetime.fromisoformat("2025-06-01T16:00:00+02:00"),
                    datetime.fromisoformat("2025-06-01T18:00:00+02:00"),
                ),
            ),
        ]:
            self.assertEqual(str2slot(raw), expected)
