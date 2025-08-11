import csv
import logging
from datetime import datetime

from django.db import transaction
from django.http import (
    Http404,
    HttpResponseForbidden,
    HttpResponseRedirect,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.timezone import now
from django.views import View, generic
from event.forms import EventBaseForm, RolesFormSet
from volunteers.forms import AvailabilityUpdateDeleteFormSet, FriendshipEditForm
from volunteers.models import VolunteerAvailability, VolunteerSlot

from .forms import ScheduleEditForm, ScheduleEventHiddenFormSet
from .models import EventSchedule, EventScheduleSlot, EventWithSchedule
from .scheduling import FriendMode, Scheduler
from .tasks import send_volunteer_slots

logger = logging.getLogger(__name__)


class IndexView(generic.ListView):
    template_name = "organizer/index.html"
    context_object_name = "latest_events_list"

    def get_queryset(self):
        return EventWithSchedule.objects.order_by("-start_date")[:5]


class ScheduleListView(generic.DetailView):
    template_name = "organizer/schedule.html"
    model = EventWithSchedule
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        kwargs = kwargs | {
            "schedules": self.object.eventschedule_set.order_by("-saved_at")
        }
        return super().get_context_data(**kwargs)


class ScheduleView(generic.DetailView):
    template_name = "organizer/schedule_detail.html"
    model = EventSchedule
    pk_field = "id"
    pk_url_kwarg = "id"

    def get_context_data(self, **kwargs):
        kwargs = kwargs | {
            "event": self.object.event,
            "slots": self.object.event.schedule_slots(),
            "missings": self.object.get_missing_by_slots(),
            "by_roles": self.object.get_schedule_by_roles(),
            "by_volunteers": self.object.get_schedule_by_volunteers(),
        }
        return super().get_context_data(**kwargs)


class ScheduleNewView(generic.detail.SingleObjectMixin, generic.TemplateView):
    model = EventWithSchedule
    context_object_name = "event"
    template_name = "organizer/schedule_edit.html"

    def update_kwargs_with_post(self, kwargs):
        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    def get_forms(self):
        self.object = self.get_object()
        base_kwargs = {
            "initial": {
                "event": self.object,
                "name": None,
                "no_update": False,
                "no_delete": True,
            },
            "prefix": "base",
        }
        form = ScheduleEditForm(**self.update_kwargs_with_post(base_kwargs))

        self.schedule = EventSchedule(
            event=self.object, type=EventSchedule.ScheduleType.EMPTY, deletable=True
        )
        slots = []
        for role in self.object.role_set.all():
            for position in range(0, role.occurence):
                for slot in role.slots_for_event:
                    slots.append(
                        EventScheduleSlot(
                            schedule=self.schedule,
                            start_date=slot.start,
                            end_date=slot.end,
                            role=role,
                            position=position,
                        )
                    )
        with transaction.atomic():
            self.schedule.save()
            [slot.save() for slot in slots]

        slots_kwargs = {
            "prefix": "slots",
            "instance": self.schedule,
        }
        formset = ScheduleEventHiddenFormSet(
            **self.update_kwargs_with_post(slots_kwargs)
        )
        return {"form": form, "formset": formset}

    def get_context_data(self, **kwargs):
        kwargs = (
            kwargs
            | self.get_forms()
            | {
                "event": self.object,
                "eventschedule": self.schedule,
                "slots": self.object.schedule_slots(),
                "roles": [
                    x
                    for role in self.object.role_set.order_by("order")
                    for x in zip([role] * role.occurence, range(0, role.occurence))
                ],
                "volunteers": {
                    v: {"availables": v.slots_for_event, "roles": {}}
                    for v in self.object.volunteeravailability_set.prefetch_related(
                        "volunteer"
                    ).order_by("volunteer__lastname", "volunteer__firstname")
                },
            }
        )
        return super().get_context_data(**kwargs)

    def form_valid(self):
        return redirect(
            "organizer:schedule_edit", slug=self.object.event.slug, id=self.object.id
        )


class ScheduleValidateView(generic.edit.DeleteView):
    model = EventSchedule
    pk_field = "id"
    pk_url_kwarg = "id"
    template_name = "organizer/schedule_confirm_validate.html"

    def get_context_data(self, **kwargs):
        kwargs = kwargs | {
            "event": self.object.event,
            "slots": self.object.event.schedule_slots(),
            "missings": self.object.get_missing_by_slots(),
            "by_roles": self.object.get_schedule_by_roles(),
            "by_volunteers": self.object.get_schedule_by_volunteers(),
        }
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        success_url = self.get_success_url()

        self.object.validated_at = now()
        self.object.save()

        send_volunteer_slots.delay(self.object, False)

        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        return reverse(
            "organizer:schedule_detail",
            kwargs={"slug": self.object.event.slug, "id": self.object.id},
        )


class ScheduleDeleteView(generic.edit.DeleteView):
    model = EventSchedule
    pk_field = "id"
    pk_url_kwarg = "id"

    def form_valid(self, form):
        self.object = self.get_object()
        can_delete = self.object.can_delete()

        if can_delete:
            return super().form_valid(form)
        else:
            raise Http404("Schedule not found to delete it")

    def get_success_url(self):
        return reverse("organizer:schedule", kwargs={"slug": self.object.event.slug})


class ScheduleEditView(generic.detail.SingleObjectMixin, generic.TemplateView):
    model = EventSchedule
    pk_field = "id"
    pk_url_kwarg = "id"
    template_name = "organizer/schedule_edit.html"

    def update_kwargs_with_post(self, kwargs):
        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    def get_forms(self):
        self.object = self.get_object()
        base_kwargs = {
            "initial": {
                "event": self.object.event,
                "name": self.object.name,
                "no_update": self.object.type == EventSchedule.ScheduleType.GENERATED,
                "no_delete": not self.object.deletable,
                "as_base": self.object.type == EventSchedule.ScheduleType.BASE,
            },
            "prefix": "base",
        }
        form = ScheduleEditForm(**self.update_kwargs_with_post(base_kwargs))

        slots_kwargs = {
            "prefix": "slots",
            "instance": self.object,
        }
        formset = ScheduleEventHiddenFormSet(
            **self.update_kwargs_with_post(slots_kwargs)
        )
        return {"form": form, "formset": formset}

    def get_context_data(self, **kwargs):
        kwargs = (
            kwargs
            | self.get_forms()
            | {
                "event": self.object.event,
                "slots": self.object.event.schedule_slots(),
                "roles": [
                    x
                    for role in self.object.event.role_set.order_by("order")
                    for x in zip([role] * role.occurence, range(0, role.occurence))
                ],
                "volunteers": {
                    v: {
                        "availables": v.slots_for_event,
                        "roles": {
                            s.slot: s
                            for s in v.eventscheduleslot_set.filter(
                                schedule=self.object
                            ).order_by("start_date")
                        },
                    }
                    for v in self.object.event.volunteeravailability_set.prefetch_related(
                        "volunteer"
                    ).order_by(
                        "volunteer__lastname", "volunteer__firstname"
                    )
                },
            }
        )
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        self.object = self.get_object()
        if self.object.validated_at is not None:
            return HttpResponseForbidden()

        forms = self.get_forms()
        if all(form.is_valid() for form in forms.values()):
            logger.error("Valid forms")
            return self.update(forms["form"], forms["formset"])
        logger.error("Invalid forms")
        logger.error(forms["form"].errors)
        logger.error(forms["formset"].errors)
        return self.form_invalid()

    def form_invalid(self):
        return self.render_to_response(self.get_context_data())

    def update(self, form, formset):
        with transaction.atomic():
            no_update = (
                "no_update" in form.cleaned_data and form.cleaned_data["no_update"]
            )
            if no_update:
                self.object.id = None
                self.object.saved_at = datetime.now()
            if form.cleaned_data["name"]:
                self.object.name = form.cleaned_data["name"]
            if "as_base" in form.cleaned_data and form.cleaned_data["as_base"]:
                self.object.type = EventSchedule.ScheduleType.BASE
            else:
                self.object.type = EventSchedule.ScheduleType.USER
            if "no_delete" in form.cleaned_data and form.cleaned_data["no_delete"]:
                self.object.deletable = False
            else:
                self.object.deletable = True

            self.object.save()

            formset.save(commit=False)
            forms = formset.forms if no_update else formset.saved_forms
            for subform in forms:
                if no_update:
                    subform.instance.id = None
                subform.instance.schedule = self.object
                subform.instance.save()

        return self.form_valid()

    def form_valid(self):
        return redirect(
            "organizer:schedule_edit", slug=self.object.event.slug, id=self.object.id
        )


class ScheduleGenerateView(generic.detail.SingleObjectMixin, View):
    model = EventWithSchedule
    context_object_name = "event"

    def get(self, request, *args, **kwargs):
        self.base = None
        if "base_id" in self.kwargs:
            self.base = get_object_or_404(EventSchedule, pk=self.kwargs["base_id"])
        self.object = self.get_object()
        scheduler = Scheduler(self.object, self.base)
        scheduler.friend_mode = FriendMode.AT_BEST
        if scheduler.is_valid:
            with transaction.atomic():
                schedule = EventSchedule(
                    event=self.object,
                    based_on=self.base,
                    type=EventSchedule.ScheduleType.GENERATED,
                )

                schedule_slots = []
                for volunteer, slots in scheduler.schedule.items():
                    for slot, role in slots.items():
                        schedule_slots.append(
                            EventScheduleSlot(
                                schedule=schedule,
                                volunteer=volunteer,
                                start_date=slot.start,
                                end_date=slot.end,
                                role=role[0],
                                position=role[1],
                            )
                        )
                for role, slots in scheduler.missing.items():
                    for slot in slots:
                        schedule_slots.append(
                            EventScheduleSlot(
                                schedule=schedule,
                                start_date=slot.start,
                                end_date=slot.end,
                                role=role[0],
                                position=role[1],
                            )
                        )

                schedule.save()
                EventScheduleSlot.objects.bulk_create(schedule_slots)

            return HttpResponseRedirect(
                reverse(
                    "organizer:schedule_detail",
                    kwargs={"slug": self.object.slug, "id": schedule.id},
                )
            )
        return HttpResponseRedirect(
            reverse("organizer:schedule", kwargs={"slug": self.object.slug})
        )


class Echo:
    def write(self, value):
        return value


class CsvView(generic.detail.SingleObjectMixin, View):
    model = EventWithSchedule
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        writer = csv.writer(Echo())
        return StreamingHttpResponse(
            (writer.writerow(row) for row in self.rows(**kwargs)),
            headers={"Content-Disposition": 'attachment; filename="volunteers.csv"'},
        )


class DumpView(CsvView):
    def rows(self, **kwargs):
        for availability in (
            self.object.volunteeravailability_set.prefetch_related(
                "volunteer", "volunteerfriendshipwaiting"
            )
            .order_by("volunteer__lastname", "volunteer__firstname")
            .all()
        ):
            row = []
            row.append(availability.volunteer.lastname)
            row.append(availability.volunteer.firstname)
            row.append(availability.volunteer.email)
            row.append(availability.volunteer.phonenumber)
            try:
                row.append(availability.volunteerfriendshipwaiting.lastname)
                row.append(availability.volunteerfriendshipwaiting.firstname)
            except (
                VolunteerAvailability.volunteerfriendshipwaiting.RelatedObjectDoesNotExist
            ):
                row.append("")
                row.append("")
            try:
                row.append(availability.friend.volunteer.lastname)
                row.append(availability.friend.volunteer.firstname)
            except AttributeError:
                row.append("")
                row.append("")

            row.append(availability.notes)
            row.append(availability.maxslot)

            for slot in availability.volunteerslot_set.order_by("start_date"):
                row.append(slot.start_date.isoformat())
                row.append(slot.end_date.isoformat())

            yield row


class DuoView(generic.detail.SingleObjectMixin, generic.FormView):
    model = EventWithSchedule
    context_object_name = "event"
    template_name = "organizer/duo.html"
    form_class = FriendshipEditForm

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
            self.initial["event"] = self.get_object()
        return form_class(**self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        return reverse("organizer:duo", kwargs={"slug": self.object.slug})

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        with transaction.atomic():
            for key, value in form.cleaned_data.items():
                if key in ["slug", "captcha"] or not value:
                    continue
                elif key.endswith("_delete"):
                    va = VolunteerAvailability.objects.get(
                        pk=int(key.removesuffix("_delete"))
                    )
                    va.delete()
                else:
                    va = VolunteerAvailability.objects.get(pk=int(key))
                    if value == "sup":
                        try:
                            va.volunteerfriendshipwaiting.delete()
                        except (
                            VolunteerAvailability.volunteerfriendshipwaiting.RelatedObjectDoesNotExist
                        ):
                            pass
                    else:
                        va.friend = VolunteerAvailability.objects.get(pk=int(value))

                        try:
                            if value is not None:
                                va.volunteerfriendshipwaiting.delete()
                        except (
                            VolunteerAvailability.volunteerfriendshipwaiting.RelatedObjectDoesNotExist
                        ):
                            pass
                        va.save()

        return super().form_valid(form)


class EventView(generic.DetailView):
    model = EventWithSchedule
    context_object_name = "event"
    template_name = "organizer/event.html"


class RolesView(generic.detail.SingleObjectMixin, generic.TemplateView):
    model = EventWithSchedule
    context_object_name = "event"
    template_name = "organizer/roles.html"

    def update_kwargs_with_post(self, kwargs):
        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    def get_forms(self):
        self.object = self.get_object()
        base_kwargs = {
            "initial": {"event": self.object},
            "prefix": "base",
        }
        form = EventBaseForm(**self.update_kwargs_with_post(base_kwargs))

        roles_kwargs = {
            "prefix": "role",
            "instance": self.object,
        }
        formset = RolesFormSet(**self.update_kwargs_with_post(roles_kwargs))
        return {"form": form, "formset": formset}

    def get_context_data(self, **kwargs):
        kwargs = kwargs | self.get_forms()
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        self.object = self.get_object()
        forms = self.get_forms()
        if all(form.is_valid() for form in forms.values()):
            logger.error("Valid forms")
            return self.update(forms["formset"])
        logger.error("Invalid forms")
        logger.error(forms["form"].errors)
        logger.error(forms["formset"].errors)
        return self.form_invalid()

    def form_invalid(self):
        return self.render_to_response(self.get_context_data())

    def update(self, formset):
        with transaction.atomic():
            formset.save(commit=False)
            for form in formset.saved_forms:
                form.instance.order = form.cleaned_data["ORDER"]
                form.save()
            for inst in formset.deleted_objects:
                inst.delete()

        return self.form_valid()

    def form_valid(self):
        return redirect("organizer:roles", slug=self.object.slug)


class AvailabilityUpdate(generic.detail.SingleObjectMixin, generic.TemplateView):
    model = EventWithSchedule
    context_object_name = "event"
    template_name = "organizer/availability.html"

    def update_kwargs_with_post(self, kwargs):
        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    def get_forms(self):
        self.object = self.get_object()
        base_kwargs = {
            "initial": {"event": self.object},
            "prefix": "base",
        }
        form = EventBaseForm(**self.update_kwargs_with_post(base_kwargs))

        availability_kwargs = {
            "prefix": "availability",
            "initial": [
                {"availability": av}
                for av in self.object.volunteeravailability_set.prefetch_related(
                    "volunteer", "friend", "event"
                )
                .order_by("volunteer__lastname", "volunteer__firstname")
                .all()
            ],
        }
        formset = AvailabilityUpdateDeleteFormSet(
            **self.update_kwargs_with_post(availability_kwargs)
        )
        return {"form": form, "formset": formset}

    def get_context_data(self, **kwargs):
        kwargs = kwargs | self.get_forms()
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        self.object = self.get_object()
        forms = self.get_forms()
        if all(form.is_valid() for form in forms.values()):
            logger.error("Valid forms")
            return self.update(forms["formset"])
        logger.error("Invalid forms")
        logger.error(forms["form"].errors)
        logger.error(forms["formset"].errors)
        return self.form_invalid()

    def form_invalid(self):
        return self.render_to_response(self.get_context_data())

    def update(self, formset):
        if formset.has_changed():
            with transaction.atomic():
                for form in formset:
                    if "DELETE" in form.cleaned_data and form.cleaned_data["DELETE"]:
                        va = VolunteerAvailability.objects.get(
                            pk=form.cleaned_data["availability_id"]
                        )
                        logger.info(f"Deleting {va.id}")
                        va.delete()
                    elif form.has_changed() and form.initial:
                        va = VolunteerAvailability.objects.get(
                            pk=form.cleaned_data["availability_id"]
                        )
                        logger.info(f"Updating {va.id}")
                        va.volunteerslot_set.clear()
                        slots = [
                            VolunteerSlot(
                                availability=va,
                                start_date=slot.start,
                                end_date=slot.end,
                            )
                            for slot in form.cleaned_data["slots"]
                        ]
                        va.categories.set(form.cleaned_data["categories"])
                        [s.save() for s in slots]

                        va.maxslot = len(slots)
                        va.save()

        return self.form_valid()

    def form_valid(self):
        return redirect("organizer:volunteers", slug=self.object.slug)
