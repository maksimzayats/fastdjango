from fastapi_template.core.user.services.user_identity import UserIdentityService


def test_identity_service_returns_stripped_email_without_domain_separator() -> None:
    service = UserIdentityService()

    assert service.normalize_email(email=" no-domain ") == "no-domain"
