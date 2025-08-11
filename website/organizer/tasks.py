import datetime
import logging
from email.mime.image import MIMEImage
from functools import lru_cache

from common.fields import Slot
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import F
from django.template.loader import render_to_string
from django.utils.timezone import now
from mailer.tasks import send_mass_mails
from volunteers.models import VolunteerFriendshipWaiting

from celery import shared_task

from .models import EventSchedule, ScheduleEventRemainder

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def clean_old_schedule(self):
    seven_days_ago = now() - datetime.timedelta(days=7)

    return EventSchedule.objects.filter(
        deletable=True, validated_at__isnull=True, saved_at__lt=seven_days_ago
    ).delete()


@lru_cache()
def plan():
    # TODO replace by a file uploaded by user
    with open("/code/volunteers/static/emails/plan.png", "rb") as f:
        plan_data = f.read()
    result = MIMEImage(plan_data)
    result.add_header("Content-ID", "<plan>")
    return result


@shared_task(bind=True)
def send_volunteer_slots(self, schedule, remainder):
    logger.info(
        f"Start of sending validated slots to volunteer for {schedule} - "
        f"Remainder: {remainder}"
    )

    mails = []
    for volunteer, roles in schedule.get_schedule_by_volunteers().items():
        logger.debug(f"Send slot for {volunteer}: {roles}")
        slots_by_role = {
            role["role"]: []
            for role in roles.values()
            if "role" in role and role["role"].with_validation_email
        }
        for slot, role_info in roles.items():
            if "role" in role_info and role_info["role"].with_validation_email:
                slots_by_role[role_info["role"]].append(slot)
        role_by_slots = {
            slot: role
            for role, slots in slots_by_role.items()
            if role.with_validation_email
            for slot in Slot.aggregate(slots)
        }

        role_by_slots = {
            slot: role_by_slots[slot]
            for slot in sorted(role_by_slots.keys())
            if role_by_slots[slot]
        }

        if not role_by_slots:
            logger.debug("No role to send for {volunteer}")
            continue

        logger.debug(f"Final slots : {role_by_slots}")

        # TODO replace static templaces by configurable by user
        text_content = render_to_string(
            "emails/validate_schedule.txt",
            context={
                "firstname": volunteer.volunteer.firstname,
                "is_remainder": remainder,
                "slots": role_by_slots,
            },
        )
        html_content = render_to_string(
            "emails/validate_schedule.html",
            context={
                "firstname": volunteer.volunteer.firstname,
                "is_remainder": remainder,
                "slots": role_by_slots,
            },
        )
        # TODO replace object of email by one configurable by user
        # TODO replace email address by one configurable by user
        msg = EmailMultiAlternatives(
            "[6h Drôme Roller] - Planning bénévole",
            text_content,
            settings.EMAIL_HOST_USER,
            [volunteer.volunteer.email],
            headers={"List-Unsubscribe": "<mailto:6hdromerollers@gmail.com>"},
        )
        msg.attach_alternative(html_content, "text/html")
        msg.attach(plan())
        # TODO replace static file by one configurable by user
        msg.attach_file("/code/volunteers/static/emails/charte.pdf")
        mails.append(msg)

    if mails:
        logger.info(f"Sending {len(mails)} mails to volunteers")
        send_mass_mails.delay(mails)
    else:
        logger.info("Not slots to send")


@shared_task(bind=True)
def volunteers_remainder(self):
    logger.info("Start of remainders computation")
    remainders = ScheduleEventRemainder.objects.prefetch_related("event").filter(
        done_at__isnull=True,
        event__start_date__date__lte=now()
        + (datetime.timedelta(days=1) * F("days_before")),
    )
    mails = []
    for remaind in remainders:
        logger.info(f"Compute remainders for {remaind.event.name} ({remaind.event.id})")
        if remaind.event.has_schedule_validated():
            send_volunteer_slots.delay(
                remaind.event.eventschedule_set.filter(validated_at__isnull=False)
                .order_by("-validated_at")
                .first(),
                True,
            )
            continue
        for volunteer in remaind.event.volunteeravailability_set.prefetch_related(
            "volunteer"
        ):
            logger.debug(
                f"Sending remainder to {volunteer.volunteer.lastname} "
                f"{volunteer.volunteer.firstname}"
            )
            try:
                waiting_friend_firstname = (
                    volunteer.volunteerfriendshipwaiting.firstname
                )
                waiting_friend_lastname = volunteer.volunteerfriendshipwaiting.lastname
            except VolunteerFriendshipWaiting.DoesNotExist:
                waiting_friend_firstname = None
                waiting_friend_lastname = None

            # TODO replace static templaces by configurable by user
            text_content = render_to_string(
                "emails/remainder.txt",
                context={
                    "firstname": volunteer.volunteer.firstname,
                    "friend_firstname": (
                        volunteer.friend.volunteer.firstname
                        if volunteer.friend
                        else None
                    ),
                    "friend_lastname": (
                        volunteer.friend.volunteer.lastname
                        if volunteer.friend
                        else None
                    ),
                    "waiting_friend_firstname": waiting_friend_firstname,
                    "waiting_friend_lastname": waiting_friend_lastname,
                    "slots": volunteer.slots,
                },
            )
            html_content = render_to_string(
                "emails/remainder.html",
                context={
                    "firstname": volunteer.volunteer.firstname,
                    "friend_firstname": (
                        volunteer.friend.volunteer.firstname
                        if volunteer.friend
                        else None
                    ),
                    "friend_lastname": (
                        volunteer.friend.volunteer.lastname
                        if volunteer.friend
                        else None
                    ),
                    "waiting_friend_firstname": waiting_friend_firstname,
                    "waiting_friend_lastname": waiting_friend_lastname,
                    "slots": volunteer.slots,
                },
            )

            # TODO replace object of email by one configurable by user
            # TODO replace email address by one configurable by user
            msg = EmailMultiAlternatives(
                "[6h Drôme Roller] - Rappel bénévole",
                text_content,
                settings.EMAIL_HOST_USER,
                [volunteer.volunteer.email],
                headers={"List-Unsubscribe": "<mailto:6hdromerollers@gmail.com>"},
            )
            msg.attach_alternative(html_content, "text/html")
            mails.append(msg)
        remaind.done_at = now()

    if mails:
        logger.info(f"Sending {len(mails)} remainders")
        send_mass_mails.delay(mails)
    else:
        logger.info("Not remainders to send")

    for remaind in remainders:
        remaind.save()
