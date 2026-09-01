import strawberry

from strawberry_django import mutations


def test_mutation_returning_interface_with_error_handling():
    @strawberry.interface
    class Project:
        name: str

    @strawberry.type
    class WebProject(Project):
        url: str

    @strawberry.type
    class ExternalProject(Project):
        provider: str

    @strawberry.type
    class Query:
        value: str = "value"

    @strawberry.type
    class Mutation:
        @mutations.mutation(handle_django_errors=True)
        def update_project(self) -> Project:
            return WebProject(name="site", url="https://example.com")

    schema = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        types=[WebProject, ExternalProject],
    )
    result = schema.execute_sync(
        """
        mutation {
          updateProject {
            __typename
            ... on WebProject {
              name
              url
            }
          }
        }
        """
    )

    assert result.errors is None
    assert result.data == {
        "updateProject": {
            "__typename": "WebProject",
            "name": "site",
            "url": "https://example.com",
        }
    }
