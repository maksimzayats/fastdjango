from fastdjango.core.exceptions import ApplicationError


class UserError(ApplicationError):
    pass


class WeakPasswordError(UserError):
    pass


class UserAlreadyExistsError(UserError):
    pass
