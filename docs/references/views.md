# View

```python
from django.urls path
from strawberry.django.views import GraphQLView, AsyncGraphQLView
from .schema import schema

urlpatterns = [
    path('graphql/sync', GraphQLView.as_view(schema=schema)),
    path('graphql', AsyncGraphQLView.as_view(schema=schema)),
]
```
