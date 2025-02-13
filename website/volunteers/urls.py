from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

app_name = "volunteers"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("<slug>/", views.EventView.as_view(), name="event"),
    path("register/<slug>/", views.RegisterAsVolunteer.as_view(), name="register"),
    path("thanks/<slug>/", views.Thanks.as_view(), name="thanks"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
