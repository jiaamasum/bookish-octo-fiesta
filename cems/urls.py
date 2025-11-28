"""
URL configuration for cems project.
"""
from django.contrib import admin
from django.urls import include, path, re_path
from accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("accounts/", include(("accounts.urls", "accounts"))),
    # Catch-all to home
    re_path(r"^.*$", account_views.fallback_to_home, name="fallback"),
]

handler404 = "accounts.views.handle_404"
