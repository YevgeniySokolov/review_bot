class OtherStatusCode(Exception):
    """Статус-код, отличный от 200."""

    pass


class APIRequestException(Exception):
    """Сбой при запросе к API."""

    pass

class TelegramException(Exception):
    """Сбой при отправке сообщения в Telegram."""

    pass
