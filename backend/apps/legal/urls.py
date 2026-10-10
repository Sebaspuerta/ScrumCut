from django.urls import path

from apps.legal import views

urlpatterns = [path("<slug:slug>/", views.document, name="legal_document")]
