"""Common litecord errors.
"""

class ApiError(Exception):
    """An API general error."""
    api_errcode = 50000
    status_code = 500


class Unauthorized(ApiError):
    """Unauthorized to use a certain route."""
    api_errcode = 40001
    status_code = 401


class UnknownUser(ApiError):
    """Unknown user."""
    api_errcode = 10013
    status_code = 404


class LitecordValidationError(ApiError):
    """A validation issue with user data."""
    status_code = 400
