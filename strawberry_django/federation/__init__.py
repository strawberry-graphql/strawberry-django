"""Federation support for strawberry-django.

This module provides Django-aware federation decorators that combine
`strawberry_django` functionality with Apollo Federation support.

- `type` - Federation-aware Django type decorator
- `interface` - Federation-aware Django interface decorator
- `field` - Federation-aware Django field decorator

The type and interface decorators automatically generate `resolve_reference`
methods for entity types (those with `@key` directives).

See docs/integrations/federation.md for full usage examples.
"""

from .field import field
from .resolve import generate_resolve_reference, resolve_model_reference
from .type import interface
from .type import type as type  # noqa: A004

__all__ = [
    "field",
    "generate_resolve_reference",
    "interface",
    "resolve_model_reference",
    "type",
]
