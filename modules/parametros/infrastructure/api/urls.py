from django.urls import path
from .views import (
    ParametersView,
    ModuleParametersView,
    CatalogView,
    SignatureUploadView,
    ValidateSignatureView
)

urlpatterns = [
    path('',                        ParametersView.as_view()),
    path('catalogo/',               CatalogView.as_view()),
    path('upload-signature/',       SignatureUploadView.as_view()),
    path('validate-signature/',     ValidateSignatureView.as_view()),
    path('<str:module>/',           ModuleParametersView.as_view()),
]
