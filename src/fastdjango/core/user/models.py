import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    def __str__(self) -> str:
        return f"User(id={self.pk}, username={self.username})"


class RefreshSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)

    refresh_token_hash = models.CharField(max_length=128, unique=True)

    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    rotation_counter = models.PositiveIntegerField(default=0)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="refresh_sessions",
    )

    def __str__(self) -> str:
        return f"RefreshSession(id={self.id}, user_id={self.user.pk})"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()
