import logging

from django import forms
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3

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
