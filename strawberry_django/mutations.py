import strawberry
from django.contrib.auth import authenticate, login, logout

@strawberry.type
class LoginMutation:

    @strawberry.mutation
    def login(info, username: str, password: str) -> str:
        request = info.context['request']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return 'ok'
        logout(request)
        return 'failed'

    @strawberry.mutation
    def logout(info) -> str:
        request = info.context['request']
        logout(request)
        return 'ok'

