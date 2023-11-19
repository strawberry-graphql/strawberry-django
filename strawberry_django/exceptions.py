class DefaultMessageError(Exception):
    """A class to define a default message with the exception definition."""

    MSG = ""

    def __init__(self, *args, message=None, **kwargs):
        if message is None:
            message = self.MSG

        super().__init__(message)
