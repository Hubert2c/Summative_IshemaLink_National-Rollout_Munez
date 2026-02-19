from django.urls import path
from .views import EBMSignReceiptView, RURAVerifyView, CustomsManifestView, AuditLogView

urlpatterns = [
    path("ebm/sign-receipt/",              EBMSignReceiptView.as_view(), name="ebm-sign"),
    path("rura/verify-license/<str:license_no>/", RURAVerifyView.as_view(), name="rura-verify"),
    path("customs/generate-manifest/",     CustomsManifestView.as_view(), name="customs-manifest"),
    path("audit/access-log/",              AuditLogView.as_view(),        name="audit-log"),
]
