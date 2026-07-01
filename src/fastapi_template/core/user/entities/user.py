from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True, slots=True)
class User:
    """Core user account state used by authentication and authorization rules."""

    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    password_hash: str
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
