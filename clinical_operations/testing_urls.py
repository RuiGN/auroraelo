from django.urls import include, path

urlpatterns = [path("api/v1/clinical-operations/", include("clinical_operations.urls"))]
