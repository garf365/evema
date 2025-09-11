import logging

from django import forms
from event.forms import EventBaseForm

from django.contrib.admin.widgets import AdminSplitDateTime
from common.forms import DraggableFormSet
from common.fields import Slot
from .models import EventSchedule, EventScheduleSlot, RoleWithSchedule, EventWithSchedule

logger = logging.getLogger(__name__)


class ScheduleEditForm(EventBaseForm):
    no_update = forms.BooleanField(required=False)
    as_base = forms.BooleanField(required=False)
    name = forms.CharField(required=False)
    no_delete = forms.BooleanField(required=False)



class RolesFormSet(
    forms.inlineformset_factory(
        EventWithSchedule,
        RoleWithSchedule,
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
                isinstance(role[0], RoleWithSchedule)
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
                isinstance(role[0], RoleWithSchedule)
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

class ScheduleEventHiddenFormSet(
    forms.inlineformset_factory(
        EventSchedule,
        EventScheduleSlot,
        formset=RoleAndSlotBasedHiddenFormSet,
        exclude=[],
        widgets={
            "volunteer": forms.HiddenInput(),
            "start_date": forms.HiddenInput(),
            "end_date": forms.HiddenInput(),
            "role": forms.HiddenInput(),
            "position": forms.HiddenInput(),
            "fixed": forms.HiddenInput(),
        },
        extra=0,
    )
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.forms:
            f.fields["volunteer"].required = False
