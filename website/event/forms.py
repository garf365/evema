import logging

from common.fields import Slot
from common.forms import DraggableFormSet
from django import forms
from django.contrib.admin.widgets import AdminSplitDateTime
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3

from .models import Event, Role

logger = logging.getLogger(__name__)


class EventBaseForm(forms.Form):
    slug = forms.CharField(widget=forms.HiddenInput())
    captcha = ReCaptchaField(widget=ReCaptchaV3(action="register"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.event = None
        if "initial" in kwargs and "event" in kwargs["initial"]:
            self.event = kwargs["initial"]["event"]
            self.fields["slug"].initial = self.event.slug


class RolesFormSet(
    forms.inlineformset_factory(
        Event,
        Role,
        formset=DraggableFormSet,
        exclude=["order"],
        extra=0,
        can_delete=True,
        can_order=True,
        widgets={
            "start_date": AdminSplitDateTime(),
            "end_date": AdminSplitDateTime(),
        },
        field_classes={
            "start_date": forms.SplitDateTimeField,
            "end_date": forms.SplitDateTimeField,
        },
    )
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.order_by("order")


# TODO write ut
class RoleAndSlotBasedHiddenFormSet(forms.BaseInlineFormSet):
    deletion_widget = forms.HiddenInput

    def __getitem__(self, index):
        try:
            role, slot = index
            if (
                isinstance(role[0], Role)
                and isinstance(role[1], int)
                and isinstance(slot, Slot)
            ):
                # TODO use next() instead
                results = [
                    form
                    for form in self.forms
                    if form.instance.role == role[0]
                    and form.instance.position == role[1]
                    and form.instance.slot == slot
                ]
                if len(results) == 1:
                    return results[0]
                raise IndexError(index)
        except (IndexError, TypeError):
            pass
        return super().__getitem__(index)

    def __contains__(self, index):
        try:
            role, slot = index
            if (
                isinstance(role[0], Role)
                and isinstance(role[1], int)
                and isinstance(slot, Slot)
            ):
                return any(
                    True
                    for form in self.forms
                    if form.instance.role == role[0]
                    and form.instance.position == role[1]
                    and form.instance.slot == slot
                )
        except (IndexError, TypeError):
            pass
        return super().__getitem__(index)
