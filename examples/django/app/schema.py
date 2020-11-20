import strawberry
from strawberry_django import ModelResolver, ModelPermissions
from .models import User, Group

class UserResolver(ModelResolver):
    model = User
    @strawberry.field
    def age_in_months(info, root) -> int:
        return root.age * 12

class GroupResolver(ModelResolver):
    model = Group
    fields = ['name', 'users']

    # only users who have group permissions can access and modify groups
    permissions_classes = [ModelPermissions]

    # queryset filtering
    def get_queryset(self):
        qs = super().get_queryset()
        # only super users can access groups
        if not self.request.user.is_superuser:
            qs = qs.none()
        return qs

@strawberry.type
class Query(UserResolver.query(), GroupResolver.query()):
    pass

@strawberry.type
class Mutation(UserResolver.mutation(), GroupResolver.mutation()):
    pass

schema = strawberry.Schema(query=Query, mutation=Mutation)
