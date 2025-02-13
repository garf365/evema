import logging

from django import forms
from event.forms import EventBaseForm, RoleAndSlotBasedHiddenFormSet

from .models import EventSchedule, EventScheduleSlot

logger = logging.getLogger(__name__)


class ScheduleEditForm(EventBaseForm):
    no_update = forms.BooleanField(required=False)
    as_base = forms.BooleanField(required=False)
    name = forms.CharField(required=False)
    no_delete = forms.BooleanField(required=False)


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
