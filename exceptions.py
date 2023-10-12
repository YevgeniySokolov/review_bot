class UnknownError(Exception):
    """Wrong from_date format."""

    pass


class NotAuthenticated(Exception):
    """Учетные данные не были предоставлены."""

    pass


class EndpointAccess(Exception):
    """Недоступность эндпоинта."""

    pass
