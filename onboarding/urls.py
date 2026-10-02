"""Routes for the onboarding domain."""

from django.urls import path

from .views import clinic_onboarding

urlpatterns = [
    path("clinic/", clinic_onboarding, name="clinic_onboarding"),
]
