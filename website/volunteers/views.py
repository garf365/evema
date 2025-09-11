import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import generic
from mailer.tasks import send_mails

from .forms import RegisterVolunteerForm
from .models import (
    EventWithVolunteers,
    Volunteer,
    VolunteerAvailability,
    VolunteerFriendshipWaiting,
    VolunteerSlot,
)

logger = logging.getLogger(__name__)


class IndexView(generic.ListView):
    template_name = "volunteers/index.html"
    context_object_name = "latest_events_list"

    def get_queryset(self):
        return EventWithVolunteers.objects.order_by("-start_date")[:5]


class EventView(generic.DetailView):
    model = EventWithVolunteers
    context_object_name = "event"
    template_name = "volunteers/event.html"


class RegisterAsVolunteer(generic.detail.SingleObjectMixin, generic.FormView):
    model = EventWithVolunteers
    context_object_name = "event"
    template_name = "volunteers/register.html"
    form_class = RegisterVolunteerForm

    def get_success_url(self):
        return reverse("volunteers:thanks", kwargs={"slug": self.object.slug})

    def get_form(self, form_class=None):
        logger.debug(f"get_form {form_class}")
        if form_class is None:
            form_class = self.get_form_class()
            self.initial["with_convention"] = self.object.convention is not None
            self.initial["slots_choices"] = self.object.volunteer_slots()
            self.initial["event"] = self.object
        return form_class(**self.get_form_kwargs())

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            print("form valid - create entry")
            return self.form_valid(form)
        print(f"invalid form - {form.errors}")
        return self.form_invalid(form)

    def form_valid(self, form):
        with transaction.atomic():
            try:
                volunteer = Volunteer.objects.get(
                    email__iexact=form.cleaned_data["email"],
                    firstname__iexact=form.cleaned_data["firstname"],
                    lastname__iexact=form.cleaned_data["lastname"],
                )
            except Volunteer.DoesNotExist:
                volunteer = Volunteer(
                    firstname=form.cleaned_data["firstname"],
                    lastname=form.cleaned_data["lastname"],
                    email=form.cleaned_data["email"],
                    phonenumber=form.cleaned_data["phone"],
                )
                volunteer.save()

            availability = VolunteerAvailability(
                event=self.object,
                volunteer=volunteer,
                maxslot=len(form.cleaned_data["slots"]),
                notes=form.cleaned_data["notes"],
            )
            availability.save()

            if form.cleaned_data["friend_firstname"]:
                friend = VolunteerFriendshipWaiting(
                    volunteeravailability=availability,
                    firstname=form.cleaned_data["friend_firstname"],
                    lastname=form.cleaned_data["friend_lastname"],
                )
                friend.save()

            slots = [
                VolunteerSlot(
                    availability=availability,
                    start_date=slot.start,
                    end_date=slot.end,
                )
                for slot in form.cleaned_data["slots"]
            ]
            [s.save() for s in slots]

        # TODO move it to tasks
        try:
            text_content = render_to_string(
                "emails/thanks.txt",
                context={
                    "firstname": form.cleaned_data["firstname"],
                    "friend_firstname": form.cleaned_data["friend_firstname"],
                    "friend_lastname": form.cleaned_data["friend_lastname"],
                    "slots": form.cleaned_data["slots"],
                },
            )
            html_content = render_to_string(
                "emails/thanks.html",
                context={
                    "firstname": form.cleaned_data["firstname"],
                    "friend_firstname": form.cleaned_data["friend_firstname"],
                    "friend_lastname": form.cleaned_data["friend_lastname"],
                    "slots": form.cleaned_data["slots"],
                },
            )

            msg = EmailMultiAlternatives(
                "[6h Drôme Roller] - Merci pour votre inscription en tant que bénévole",
                text_content,
                settings.EMAIL_HOST_USER,
                [form.cleaned_data["email"]],
                headers={"List-Unsubscribe": "<mailto:6hdromerollers@gmail.com>"},
            )
            msg.attach_alternative(html_content, "text/html")
            send_mails.delay([msg])
        except Exception as e:
            logger.debug(f"Can't send email {e}")

        return super().form_valid(form)


class Thanks(generic.DetailView):
    model = EventWithVolunteers
    template_name = "volunteers/thanks.html"
