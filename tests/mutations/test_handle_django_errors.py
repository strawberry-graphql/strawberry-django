import enum
from typing import Any

import pytest
import strawberry
from strawberry.scalars import JSON

from strawberry_django import mutations


@strawberry.enum
class Status(enum.Enum):
    ACTIVE = "active"


@strawberry.input(name="ProjectData")
class ProjectInput:
    name: str = "project"


@strawberry.type
class Project:
    name: str


@strawberry.type
class Query:
    value: str = "value"


@pytest.mark.parametrize(
    ("return_type", "type_name"),
    [
        (bool, "bool"),
        (strawberry.ID, "ID"),
        (JSON, "JSON"),
        (Status, "Status"),
        (list[int], "int"),
        (None, "None"),
        (ProjectInput, "ProjectData"),
        (Project | ProjectInput, "ProjectData"),
    ],
)
def test_error_handling_requires_object_return_type(return_type: Any, type_name: str):
    with pytest.raises(
        TypeError,
        match=(
            r"^Mutation `update_project` can't handle django errors, as it returns"
            rf" `{type_name}`\. "
        ),
    ):

        @strawberry.type
        class Mutation:
            @mutations.mutation(handle_django_errors=True)
            def update_project(self) -> return_type:  # type: ignore
                raise NotImplementedError


@pytest.mark.parametrize("return_type", [bool, Status, list[int]])
def test_non_object_return_type_without_error_handling(return_type: Any):
    @strawberry.type
    class Mutation:
        @mutations.mutation(handle_django_errors=False)
        def update_project(self) -> return_type:  # type: ignore
            raise NotImplementedError

    schema = strawberry.Schema(query=Query, mutation=Mutation)
    assert "UpdateProjectPayload" not in str(schema)


@pytest.mark.parametrize("return_type", [Project, Project | None, list[Project]])
def test_object_return_type_with_error_handling(return_type: Any):
    @strawberry.type
    class Mutation:
        @mutations.mutation(handle_django_errors=True)
        def update_project(self) -> return_type:  # type: ignore
            raise NotImplementedError

    schema = strawberry.Schema(query=Query, mutation=Mutation)
    assert "union UpdateProjectPayload = Project | OperationInfo" in str(schema)
