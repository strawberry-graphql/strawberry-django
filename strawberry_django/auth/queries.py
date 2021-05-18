import strawberry_django

def current_user():
    @strawberry_django.field
    def current_user(info):
        return info.context.request.user
    return current_user
