from typing import TYPE_CHECKING

from django.contrib import admin

from fastdjango.core.user.models import User

if TYPE_CHECKING:
    UserAdminBase = admin.ModelAdmin[User]
else:
    UserAdminBase = admin.ModelAdmin


@admin.register(User)
class UserAdmin(UserAdminBase):
    filter_horizontal = ("groups", "user_permissions")

    list_display = (
        "username",
        "is_active",
        "is_staff",
        "is_superuser",
    )
