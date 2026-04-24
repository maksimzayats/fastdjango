from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    def __str__(self) -> str:
        return f"User(id={self.pk}, username={self.username})"
