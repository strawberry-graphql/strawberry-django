import strawberry
from django.contrib import auth
from ..resolvers import django_resolver

@django_resolver
def resolve_login(info, username: str, password: str):
    request = info.context.request
    user = auth.authenticate(request, username=username, password=password)
    if user is not None:
        auth.login(request, user)
        return user
    auth.logout(request)
    return None

@django_resolver
def resolve_logout(info) -> bool:
    request = info.context.request
    ret = request.user.is_authenticated
    auth.logout(request)
    return ret

def login():
    mutation = strawberry.mutation(resolver=resolve_login)
    mutation.is_optional = True
    return mutation

def logout():
    return strawberry.mutation(resolver=resolve_logout)
