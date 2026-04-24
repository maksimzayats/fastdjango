from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("email address", unique=True)

    def __str__(self) -> str:
        return f"User(id={self.pk}, username={self.username})"
