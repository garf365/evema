import logging

from common.fields import SlotsField
from django import forms
from event.forms import EventBaseForm

from .models import Volunteer, VolunteerAvailability

logger = logging.getLogger(__name__)


class AvailabilityUpdateDeleteForm(forms.Form):
    availability_id = forms.IntegerField(widget=forms.HiddenInput())
    slots = SlotsField(required=False, choices=[])
    categories = forms.MultipleChoiceField(
        required=False, widget=forms.CheckboxSelectMultiple, choices=[]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "initial" in kwargs and "slots_choices" in kwargs["initial"]:
            self.fields["slots"].choices = kwargs["initial"]["slots_choices"]
        self.availability = None
        if "initial" in kwargs and "availability" in kwargs["initial"]:
            self.availability = kwargs["initial"]["availability"]
            self.fields["availability_id"].initial = self.availability.id
            self.fields["slots"].choices = [
                (str(s), s) for s in self.availability.event.schedule_slots()
            ]
            slots = [
                slot
                for slot in self.availability.event.schedule_slots()
                if any(
                    slot.is_contained_by(s.slot)
                    for s in self.availability.volunteerslot_set.all()
                )
            ]
            self.fields["slots"].initial = slots
            self.fields["categories"].choices = [
                (c.id, c.name)
                for c in self.availability.event.rolecategory_set.order_by("name").all()
            ]
            self.fields["categories"].initial = [
                c.id for c in self.availability.categories.all()
            ]


AvailabilityUpdateDeleteFormSet = forms.formset_factory(
    AvailabilityUpdateDeleteForm, can_delete=True, extra=0
)


class FriendshipEditForm(EventBaseForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

        if self.event is not None:
            queryset_availabilities = (
                self.event.volunteeravailability_set.prefetch_related("volunteer")
                .order_by("volunteer__lastname", "volunteer__firstname")
                .all()
            )
            for availability in queryset_availabilities:
                choices = [("", "---------")]
                try:
                    if availability.volunteerfriendshipwaiting:
                        choices.append(("sup", "~~~~ supprimer ~~~~"))
                except (
                    VolunteerAvailability.volunteerfriendshipwaiting.RelatedObjectDoesNotExist
                ):
                    pass
                choices += [
                    (V.id, str(V.volunteer))
                    for V in queryset_availabilities.exclude(pk=availability.id).all()
                ]
                self.fields[str(availability.id)] = forms.ChoiceField(
                    label=str(availability.volunteer),
                    choices=choices,
                    required=False,
                    initial=(
                        (availability.friend.id, availability.friend)
                        if availability.friend is not None
                        else None
                    ),
                    widget=forms.Select(attrs={"class": "form-control"}),
                )
                self.fields[str(availability.id)].label_from_instance = (
                    lambda obj: obj.volunteer
                )
                self.fields[str(availability.id)].availability = availability


class RegisterVolunteerForm(EventBaseForm):
    firstname = forms.CharField(max_length=100)
    lastname = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    friend_firstname = forms.CharField(max_length=100, required=False)
    friend_lastname = forms.CharField(max_length=100, required=False)
    slots = SlotsField()
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": "5"}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "initial" in kwargs and "with_convention" in kwargs["initial"]:
            is_required = bool(kwargs["initial"]["with_convention"])
            if is_required:
                self.fields["convention"] = forms.BooleanField(required=is_required)
                self.fields["convention"].required = is_required
                self.fields["convention"].widget.required = is_required
        if "initial" in kwargs and "slots_choices" in kwargs["initial"]:
            self.fields["slots"].choices = [
                (str(slot), slot) for slot in kwargs["initial"]["slots_choices"]
            ]

        for visible in self.visible_fields():
            if visible.name != "convention":
                visible.field.widget.attrs["class"] = "form-control"

    # TODO translate message
    def clean(self):
        super().clean()

        logger.debug("Cleaning volunteer form data.")
        firstname = self.cleaned_data.get("firstname")
        lastname = self.cleaned_data.get("lastname")
        email = self.cleaned_data.get("email")
        friend_firstname = self.cleaned_data.get("friend_firstname")
        friend_lastname = self.cleaned_data.get("friend_lastname")

        if bool(friend_firstname) != bool(friend_lastname):
            self.add_error(
                "friend_lastname",
                "Vous devez renseigner le nom et le prénom de votre binôme",
            )

        try:
            logger.debug("Checking if an existing volunteer already exists.")
            volunteer = Volunteer.objects.get(
                email__iexact=email,
                firstname__iexact=firstname,
                lastname__iexact=lastname,
            )
            VolunteerAvailability.objects.get(event=self.event, volunteer=volunteer)
            self.add_error(
                "lastname",
                "Il semblerait que vous vous soyez déjà inscrit comme bénévole. "
                "Merci de contacter un organisateur pour plus d'information",
            )
            logger.debug("Volunteer already createed, form is unvalid.")
        except (Volunteer.DoesNotExist, VolunteerAvailability.DoesNotExist):
            logger.debug("Volunteer is new.")
