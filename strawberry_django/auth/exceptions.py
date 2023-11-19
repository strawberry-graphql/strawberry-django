from strawberry_django.exceptions import DefaultMessageError


class IncorrectUsernamePasswordError(DefaultMessageError):
    MSG = "Incorrect username or password."


class UserNotLoggedInError(DefaultMessageError):
    MSG = "User is not logged in."
