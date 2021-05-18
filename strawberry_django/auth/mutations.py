import strawberry
from django.contrib import auth
from ..resolvers import django_resolver

def login():
    @strawberry.mutation
    @django_resolver
    def login(info, username: str, password: str):
        request = info.context.request
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return user
        auth.logout(request)
        return request.user
    return login

def logout():
    @strawberry.mutation
    @django_resolver
    def logout(info) -> str:
        request = info.context.request
        auth.logout(request)
        return ''
    return logout

