import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from modern_python_template.core.user.models import User


class RefreshSession(models.Model):
    id = models.UUIDField(verbose_name="ID", primary_key=True, default=uuid.uuid7, editable=False)

    refresh_token_hash = models.CharField(
        verbose_name="refresh token hash",
        max_length=128,
        unique=True,
    )

    user_agent = models.TextField(verbose_name="user agent", blank=True)
    ip_address_trace = models.TextField(verbose_name="IP address trace", blank=True, default="")

    created_at = models.DateTimeField(verbose_name="created at", auto_now_add=True)
    last_used_at = models.DateTimeField(verbose_name="last used at", null=True, blank=True)

    expires_at = models.DateTimeField(verbose_name="expires at")
    revoked_at = models.DateTimeField(verbose_name="revoked at", null=True, blank=True)

    rotation_counter = models.PositiveIntegerField(verbose_name="rotation counter", default=0)

    user: models.ForeignKey[User, User] = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresh_sessions",
        verbose_name="user",
    )

    class Meta:
        verbose_name = "refresh session"
        verbose_name_plural = "refresh sessions"

    def __str__(self) -> str:
        return f"RefreshSession(id={self.id}, user_id={self.user.pk})"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()
