"""URL routes for the team side of exercises (catalog, assignment, review).

Patients use goals, exercises and low-energy mode only in the mobile app.
"""

from django.urls import path

from .exercise_views import (
    exercise_assign_view,
    exercise_catalog,
    exercise_execution_detail_view,
    exercise_form,
)

urlpatterns = [
    path("exercicios/catalogo/", exercise_catalog, name="exercise_catalog"),
    path("exercicios/catalogo/novo/", exercise_form, name="exercise_create"),
    path(
        "exercicios/catalogo/<uuid:exercise_id>/editar/",
        exercise_form,
        name="exercise_edit",
    ),
    path(
        "exercicios/catalogo/<uuid:exercise_id>/atribuir/",
        exercise_assign_view,
        name="exercise_assign",
    ),
    path(
        "exercicios/execucoes/<uuid:execution_id>/",
        exercise_execution_detail_view,
        name="exercise_execution_detail",
    ),
]
