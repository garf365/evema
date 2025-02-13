import logging

from django import forms

logger = logging.getLogger(__name__)


class DraggableFormSet(forms.BaseInlineFormSet):
    ordering_widget = forms.HiddenInput
