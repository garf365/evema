from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

app_name = "organizer"
urlpatterns = [
    path("", login_required(views.IndexView.as_view()), name="index"),
    path("<slug>/", login_required(views.EventView.as_view()), name="event"),
    path("duo/<slug>/", login_required(views.DuoView.as_view()), name="duo"),
    path(
        "planning/<slug>/",
        login_required(views.ScheduleListView.as_view()),
        name="schedule",
    ),
    path(
        "planning/<slug>/generate/",
        login_required(views.ScheduleGenerateView.as_view()),
        name="schedule_generate",
    ),
    path(
        "planning/<slug>/new/",
        login_required(views.ScheduleNewView.as_view()),
        name="schedule_new",
    ),
    path(
        "planning/<slug>/<id>/edit/",
        login_required(views.ScheduleEditView.as_view()),
        name="schedule_edit",
    ),
    path(
        "planning/<slug>/<id>/delete/",
        login_required(views.ScheduleDeleteView.as_view()),
        name="schedule_delete",
    ),
    path(
        "planning/<slug>/<id>/validate/",
        login_required(views.ScheduleValidateView.as_view()),
        name="schedule_validate",
    ),
    path(
        "planning/<slug>/<base_id>/complete/",
        login_required(views.ScheduleGenerateView.as_view()),
        name="schedule_complete",
    ),
    path(
        "planning/<slug>/<id>/",
        login_required(views.ScheduleView.as_view()),
        name="schedule_detail",
    ),
    path("roles/<slug>/", login_required(views.RolesView.as_view()), name="roles"),
    path(
        "volunteers/<slug>/",
        login_required(views.AvailabilityUpdate.as_view()),
        name="volunteers",
    ),
    path("dump/<slug>/", login_required(views.DumpView.as_view()), name="dump"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
