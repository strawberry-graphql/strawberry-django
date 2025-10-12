import strawberry


@strawberry.type
class Query:
    @strawberry.field
    def hello(self, name: str | None = None) -> str:
        return f"Hello {name or 'world'}"


schema = strawberry.Schema(Query)
