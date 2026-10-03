"""Staff routes of the wellness domain (``/bem-estar/``)."""

from django.urls import path

from . import views

app_name = "wellness"

urlpatterns = [
    path(
        "recursos-de-crise/",
        views.crisis_resources,
        name="crisis_resources",
    ),
]
