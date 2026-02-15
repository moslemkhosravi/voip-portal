from django.urls import path
from . import views

urlpatterns = [
    path("api/sso/issue", views.api_issue_sso),
    path("softphone", views.softphone_page),

    path("voip-admin/", views.admin_home),
    path("voip-admin/settings", views.admin_settings),
    path("voip-admin/extensions", views.admin_extensions),
    path("voip-admin/provisioning/start", views.admin_provisioning_start),
    path("voip-admin/provisioning/<int:run_id>", views.admin_provisioning_view),
    path("voip-admin/calls", views.admin_calls),

    path("api/calls/live", views.api_live_calls),
    path("api/spy", views.api_spy_action),
]
