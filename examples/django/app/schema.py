from typing import List
import strawberry
from strawberry_django import ModelResolver, ModelPermissions
from .models import User, Group

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

class UserResolver(ModelResolver):
    model = User
    @strawberry.field
    def age_in_months(self, info, root) -> int:
        return root.age * 12

    # "ModelResolver.output_type" is a "strawberry.type".
    # So we can use it in any "strawberry.field".
    @strawberry.field
    def groups(self, info, root) -> List[GroupResolver.output_type]:
        if not info.context["request"].user.is_superuser:
            return root.groups.none()
        return root.groups.all()

@strawberry.type
class Query(UserResolver.query(), GroupResolver.query()):
    pass

@strawberry.type
class Mutation(UserResolver.mutation(), GroupResolver.mutation()):
    pass

schema = strawberry.Schema(query=Query, mutation=Mutation)
