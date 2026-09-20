from django.urls import path

from .forms import COMMANDS
from .views import endpoint

app_name = "clinical_operations"
urlpatterns = [
    path(f"{resource}/", endpoint, {"resource": resource}, name=resource)
    for resource in COMMANDS
]
