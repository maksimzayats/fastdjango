from django.contrib import admin
from django.http import HttpRequest

from fastdjango.core.authentication.models import RefreshSession


@admin.register(RefreshSession)
class RefreshSessionAdmin(admin.ModelAdmin[RefreshSession]):
    list_display = (
        "id",
        "user",
        "created_at",
        "last_used_at",
        "expires_at",
        "revoked_at",
        "rotation_counter",
    )
    list_filter = (
        "created_at",
        "last_used_at",
        "expires_at",
        "revoked_at",
    )
    search_fields = (
        "id",
        "user__username",
        "user__email",
        "user_agent",
        "ip_address_trace",
    )
    readonly_fields = (
        "id",
        "refresh_token_hash",
        "user",
        "user_agent",
        "ip_address_trace",
        "created_at",
        "last_used_at",
        "expires_at",
        "revoked_at",
        "rotation_counter",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, _request: HttpRequest) -> bool:
        return False
