from typing import Iterator

from strawberry.schema.execute import validate_document

from .django_cache_base import DjangoCacheBase


class DjangoValidationCache(DjangoCacheBase):
    def on_validate(self) -> Iterator[None]:
        execution_context = self.execution_context

        errors = self.execute_cached(
            validate_document,
            execution_context.schema._schema,
            execution_context.graphql_document,
            execution_context.validation_rules,
        )
        execution_context.errors = errors
        yield None
