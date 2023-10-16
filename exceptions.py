class UnknownError(Exception):
    """Wrong from_date format."""

    pass


class NotAuthenticated(Exception):
    """Учетные данные не были предоставлены."""

    pass


class InternalServerError(Exception):
    """Internal Server Error."""

    pass


class NoContent(Exception):
    """No Content."""

    pass
