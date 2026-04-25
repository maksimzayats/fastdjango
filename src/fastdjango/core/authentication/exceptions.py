from fastdjango.core.exceptions import ApplicationError


class AuthenticationError(ApplicationError):
    pass


class InvalidCredentialsError(AuthenticationError):
    pass


class RefreshTokenError(AuthenticationError):
    pass


class InvalidRefreshTokenError(RefreshTokenError):
    pass


class ExpiredRefreshTokenError(RefreshTokenError):
    pass
