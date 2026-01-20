from django.contrib import admin

from core.user.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin[User]):
    filter_horizontal = ("groups", "user_permissions")

    list_display = (
        "username",
        "is_active",
        "is_staff",
        "is_superuser",
    )
