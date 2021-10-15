
import strawberry
import strawberry.django
from typing import Optional, List


@strawberry.type
class Task:
    id: strawberry.ID
    name: str
    description: Optional[str]
    # ...

@strawberry.type
class TaskQueries:
    # TASK
    tasks: List[Task] = strawberry.django.field()


schema = strawberry.Schema(query=TaskQueries)