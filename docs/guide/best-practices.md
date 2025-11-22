# Best Practices

This guide covers best practices for building production-ready GraphQL APIs with Strawberry Django, including project structure, security, testing, and maintainability.

## Table of Contents

- [Project Structure](#project-structure)
- [Type Organization](#type-organization)
- [Security](#security)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Performance](#performance)
- [Code Quality](#code-quality)
- [Documentation](#documentation)
- [Deployment](#deployment)
- [Common Pitfalls](#common-pitfalls)

## Project Structure

Organize your GraphQL code for maintainability and scalability.

### Recommended Structure

```
myproject/
├── manage.py
├── myproject/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schema/
│   │   │   ├── __init__.py
│   │   │   ├── types.py
│   │   │   ├── queries.py
│   │   │   ├── mutations.py
│   │   │   └── inputs.py
│   │   └── tests/
│   │       ├── test_queries.py
│   │       └── test_mutations.py
│   ├── products/
│   │   ├── models.py
│   │   └── schema/
│   │       ├── types.py
│   │       ├── queries.py
│   │       └── mutations.py
│   └── orders/
│       ├── models.py
│       └── schema/
│           ├── types.py
│           ├── queries.py
│           └── mutations.py
└── schema.py  # Root schema combining all apps
```

### Root Schema

```python
# schema.py
import strawberry
from apps.users.schema import queries as user_queries
from apps.users.schema import mutations as user_mutations
from apps.products.schema import queries as product_queries
from apps.products.schema import mutations as product_mutations
from apps.orders.schema import queries as order_queries
from apps.orders.schema import mutations as order_mutations

@strawberry.type
class Query(
    user_queries.Query,
    product_queries.Query,
    order_queries.Query,
):
    """Root query combining all app queries"""
    pass

@strawberry.type
class Mutation(
    user_mutations.Mutation,
    product_mutations.Mutation,
    order_mutations.Mutation,
):
    """Root mutation combining all app mutations"""
    pass

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DjangoOptimizerExtension(),
    ]
)
```

### App-Level Schema Organization

```python
# apps/users/schema/__init__.py
from .types import UserType, ProfileType
from .queries import Query
from .mutations import Mutation
from .inputs import CreateUserInput, UpdateUserInput

__all__ = [
    'UserType',
    'ProfileType',
    'Query',
    'Mutation',
    'CreateUserInput',
    'UpdateUserInput',
]
```

```python
# apps/users/schema/types.py
import strawberry
from strawberry_django import type as django_type
from .. import models

@django_type(models.User)
class UserType:
    id: strawberry.ID
    email: str
    username: str
    profile: 'ProfileType'

@django_type(models.Profile)
class ProfileType:
    bio: str
    avatar_url: str
```

```python
# apps/users/schema/queries.py
import strawberry
from typing import List, Optional
from .types import UserType

@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: strawberry.ID) -> Optional[UserType]:
        return User.objects.filter(id=id).first()

    @strawberry.field
    def users(self) -> List[UserType]:
        return User.objects.all()
```

```python
# apps/users/schema/mutations.py
import strawberry
from strawberry_django import mutations
from .types import UserType
from .inputs import CreateUserInput
from .. import models

@strawberry.type
class Mutation:
    create_user: UserType = mutations.create(
        models.User,
        handle_django_errors=True
    )

    update_user: UserType = mutations.update(
        models.User,
        handle_django_errors=True
    )
```

## Type Organization

### Separate Input and Output Types

```python
# Good: Separate input and output types
@strawberry.input
class CreateUserInput:
    email: str
    username: str
    password: str

@strawberry_django.type(User)
class UserType:
    id: strawberry.ID
    email: str
    username: str
    created_at: datetime

# Avoid: Using same type for input and output
@strawberry.type
class User:  # Don't use for both!
    email: str
    username: str
```

### Use Partial Types for Updates

```python
import strawberry
from typing import Optional

@strawberry.input
class CreateUserInput:
    """All fields required for creation"""
    email: str
    username: str
    password: str

@strawberry.input
class UpdateUserInput:
    """All fields optional for updates"""
    email: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
```

### Reusable Type Fragments

```python
# Common fields shared across types
@strawberry.interface
class Timestamped:
    created_at: datetime
    updated_at: datetime

@strawberry_django.type(User)
class UserType(Timestamped):
    id: strawberry.ID
    email: str
    username: str
    # Inherits created_at and updated_at

@strawberry_django.type(Post)
class PostType(Timestamped):
    id: strawberry.ID
    title: str
    content: str
    # Inherits created_at and updated_at
```

### Type Naming Conventions

```python
# Clear, consistent naming
# Models: User, Product, Order
# Output types: UserType, ProductType, OrderType
# Input types: CreateUserInput, UpdateUserInput
# Filter types: UserFilter, ProductFilter
# Enums: UserRole, OrderStatus

# Good examples
@strawberry_django.type(User)
class UserType:
    pass

@strawberry.input
class CreateUserInput:
    pass

@strawberry.enum
class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"

# Avoid generic names
@strawberry.type
class Data:  # Too generic!
    pass

@strawberry.input
class Input:  # Too generic!
    pass
```

## Security

### Authentication

```python
import strawberry
from strawberry.types import Info
from django.contrib.auth.models import AnonymousUser

def is_authenticated(info: Info) -> bool:
    """Check if user is authenticated"""
    return info.context.request.user.is_authenticated

@strawberry.type
class Query:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def me(self, info: Info) -> UserType:
        """Get current user (requires authentication)"""
        return info.context.request.user
```

### Authorization

```python
from strawberry.permission import BasePermission
from strawberry.types import Info
from typing import Any

class IsOwner(BasePermission):
    """User must own the resource"""
    message = "You don't have permission to access this resource"

    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        user = info.context.request.user

        # Check ownership
        if hasattr(source, 'user_id'):
            return source.user_id == user.id

        if hasattr(source, 'owner'):
            return source.owner == user

        return False

@strawberry_django.type(Post)
class PostType:
    title: str
    content: str

    @strawberry.field(permission_classes=[IsOwner])
    def private_notes(self) -> str:
        """Only owner can see private notes"""
        return self.notes
```

### Input Validation

```python
import strawberry
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator

@strawberry.input
class CreateUserInput:
    email: str
    username: str
    password: str

    def __post_init__(self):
        """Validate input"""
        errors = {}

        # Email validation
        validator = EmailValidator()
        try:
            validator(self.email)
        except ValidationError:
            errors['email'] = "Invalid email format"

        # Username validation
        if len(self.username) < 3:
            errors['username'] = "Username must be at least 3 characters"

        # Password validation
        if len(self.password) < 8:
            errors['password'] = "Password must be at least 8 characters"

        if errors:
            raise ValidationError(errors)
```

### Rate Limiting

```python
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

def rate_limit(key_prefix: str, limit: int, period: int):
    """Rate limiting decorator"""
    def decorator(func):
        def wrapper(root, info: Info, **kwargs):
            user = info.context.request.user
            key = f"{key_prefix}:{user.id if user.is_authenticated else info.context.request.META.get('REMOTE_ADDR')}"

            count = cache.get(key, 0)
            if count >= limit:
                raise PermissionDenied(f"Rate limit exceeded. Try again in {period} seconds.")

            cache.set(key, count + 1, period)
            return func(root, info, **kwargs)

        return wrapper
    return decorator

@strawberry.type
class Mutation:
    @strawberry.mutation
    @rate_limit('create_post', limit=10, period=3600)  # 10 per hour
    def create_post(self, info: Info, title: str, content: str) -> PostType:
        # Create post
        pass
```

### SQL Injection Prevention

```python
# Good: Using Django ORM (prevents SQL injection)
User.objects.filter(email=user_email)

# Good: Parameterized queries
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT * FROM users WHERE email = %s", [user_email])

# NEVER: String formatting
# Bad: Vulnerable to SQL injection!
cursor.execute(f"SELECT * FROM users WHERE email = '{user_email}'")
```

### Sensitive Data

```python
import strawberry
from strawberry_django import type as django_type

@django_type(User)
class UserType:
    id: strawberry.ID
    email: str
    username: str
    # Don't expose sensitive fields!
    # password: str  ❌ Never expose password hashes
    # api_key: str   ❌ Never expose API keys

    @strawberry.field
    def email_masked(self) -> str:
        """Mask email for privacy"""
        local, domain = self.email.split('@')
        return f"{local[0]}***@{domain}"

@django_type(CreditCard)
class CreditCardType:
    last_four: str  # Only expose last 4 digits
    brand: str
    # card_number: str  ❌ Never expose full card number
    # cvv: str          ❌ Never expose CVV
```

### CSRF Protection

```python
# settings.py
STRAWBERRY_DJANGO = {
    'CSRF_ENABLED': True,  # Enable CSRF for mutations
}

# In your GraphQL view
from strawberry_django.views import GraphQLView as BaseGraphQLView
from django.views.decorators.csrf import csrf_protect

class GraphQLView(BaseGraphQLView):
    @csrf_protect
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
```

## Error Handling

### Structured Error Responses

```python
import strawberry
from typing import Union, List

@strawberry.type
class ValidationError:
    field: str
    message: str

@strawberry.type
class UserSuccess:
    user: UserType
    message: str

@strawberry.type
class UserError:
    errors: List[ValidationError]

# Use union types for error handling
CreateUserResult = strawberry.union("CreateUserResult", [UserSuccess, UserError])

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, data: CreateUserInput) -> CreateUserResult:
        try:
            user = User.objects.create(**data)
            return UserSuccess(user=user, message="User created successfully")
        except ValidationError as e:
            errors = [ValidationError(field=k, message=v) for k, v in e.message_dict.items()]
            return UserError(errors=errors)
```

### Use handle_django_errors

```python
# Good: Automatic Django error handling
@strawberry.type
class Mutation:
    create_user: UserType = mutations.create(
        models.User,
        handle_django_errors=True  # Automatically handles ValidationError
    )

# Result format includes error messages
"""
{
  "createUser": {
    "__typename": "OperationInfo",
    "messages": [
      {
        "field": "email",
        "message": "Email already exists",
        "kind": "VALIDATION"
      }
    ]
  }
}
"""
```

### Custom Exception Handling

```python
from strawberry.types import Info
from typing import Any

class GraphQLContext:
    def __init__(self, request):
        self.request = request

def custom_context_getter(request):
    return GraphQLContext(request)

async def custom_process_errors(errors: List[Any], info: Info):
    """Custom error processor"""
    processed_errors = []

    for error in errors:
        # Log errors for monitoring
        logger.error(f"GraphQL Error: {error}")

        # Sanitize error messages for production
        if not settings.DEBUG:
            error.message = "An error occurred"

        processed_errors.append(error)

    return processed_errors

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    error_formatter=custom_process_errors,
)
```

## Testing

### Query Testing

```python
# tests/test_queries.py
import pytest
from strawberry.test import BaseGraphQLTestClient
from django.test import RequestFactory
from myproject.schema import schema

@pytest.fixture
def graphql_client(db):
    """GraphQL test client"""
    factory = RequestFactory()
    request = factory.get('/graphql/')

    class Client(BaseGraphQLTestClient):
        def __init__(self):
            super().__init__(schema)
            self.request = request

    return Client()

def test_user_query(graphql_client, user):
    """Test user query"""
    query = """
        query GetUser($id: ID!) {
            user(id: $id) {
                id
                email
                username
            }
        }
    """

    result = graphql_client.query(
        query,
        variables={'id': user.id}
    )

    assert result.errors is None
    assert result.data['user']['email'] == user.email
```

### Mutation Testing

```python
def test_create_user_mutation(graphql_client):
    """Test user creation"""
    mutation = """
        mutation CreateUser($data: CreateUserInput!) {
            createUser(data: $data) {
                ... on UserType {
                    id
                    email
                    username
                }
                ... on OperationInfo {
                    messages {
                        field
                        message
                    }
                }
            }
        }
    """

    result = graphql_client.query(
        mutation,
        variables={
            'data': {
                'email': 'test@example.com',
                'username': 'testuser',
                'password': 'testpass123'
            }
        }
    )

    assert result.errors is None
    assert result.data['createUser']['email'] == 'test@example.com'
```

### Permission Testing

```python
def test_unauthorized_access(graphql_client):
    """Test that unauthenticated users can't access protected resources"""
    query = """
        query {
            me {
                id
                email
            }
        }
    """

    result = graphql_client.query(query)

    # Should return error for unauthenticated user
    assert result.errors is not None
    assert 'authentication required' in str(result.errors[0]).lower()
```

### Integration Testing

```python
from django.test import TestCase
from graphene.test import Client

class GraphQLIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client(schema)
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser'
        )

    def test_full_workflow(self):
        """Test complete user workflow"""
        # 1. Create user
        create_result = self.client.execute(create_user_mutation)
        user_id = create_result['data']['createUser']['id']

        # 2. Query user
        query_result = self.client.execute(
            get_user_query,
            variables={'id': user_id}
        )
        assert query_result['data']['user']['id'] == user_id

        # 3. Update user
        update_result = self.client.execute(
            update_user_mutation,
            variables={'id': user_id, 'username': 'newname'}
        )
        assert update_result['data']['updateUser']['username'] == 'newname'
```

### Performance Testing

```python
from django.test import override_settings
from django.db import connection, reset_queries

@override_settings(DEBUG=True)
def test_query_performance(graphql_client):
    """Test that queries are optimized (no N+1)"""
    # Create test data
    authors = [Author.objects.create(name=f"Author {i}") for i in range(10)]
    for author in authors:
        Book.objects.create(title=f"Book by {author.name}", author=author)

    query = """
        query {
            books {
                title
                author {
                    name
                }
            }
        }
    """

    reset_queries()
    result = graphql_client.query(query)

    # Should use only 2 queries (books + authors join)
    assert len(connection.queries) <= 2
    assert result.errors is None
```

## Performance

See the [Performance Guide](performance.md) for comprehensive optimization strategies.

### Key Performance Practices

```python
# 1. Always use Query Optimizer
schema = strawberry.Schema(
    query=Query,
    extensions=[DjangoOptimizerExtension()]
)

# 2. Always paginate
@strawberry.field
def books(self, pagination: OffsetPaginationInput) -> List[BookType]:
    return Book.objects.all()[pagination.offset:pagination.limit]

# 3. Add database indexes
class Book(models.Model):
    title = models.CharField(max_length=200, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['author', 'publication_date'])
        ]

# 4. Use bulk operations
Book.objects.filter(id__in=ids).update(is_published=True)

# 5. Cache expensive operations
from django.core.cache import cache

@strawberry.field
def statistics(self) -> StatsType:
    cached = cache.get('statistics')
    if cached:
        return cached

    stats = compute_expensive_statistics()
    cache.set('statistics', stats, 300)
    return stats
```

## Code Quality

### Type Hints

```python
# Good: Full type hints
from typing import List, Optional

@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: strawberry.ID) -> Optional[UserType]:
        return User.objects.filter(id=id).first()

    @strawberry.field
    def users(self, limit: int = 10) -> List[UserType]:
        return User.objects.all()[:limit]

# Avoid: Missing type hints
@strawberry.field
def user(self, id):  # Missing types!
    return User.objects.get(id=id)
```

### Docstrings

```python
@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: strawberry.ID) -> Optional[UserType]:
        """
        Get a user by ID.

        Args:
            id: The user's unique identifier

        Returns:
            User object if found, None otherwise
        """
        return User.objects.filter(id=id).first()
```

### Linting and Formatting

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py310']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.10"
plugins = ["mypy_django_plugin.main", "strawberry.ext.mypy_plugin"]
strict = true

[[tool.mypy.overrides]]
module = "myapp.*"
disallow_untyped_defs = true
```

### Code Review Checklist

- [ ] All queries paginated
- [ ] Query optimizer enabled
- [ ] Permissions checked
- [ ] Input validated
- [ ] Errors handled properly
- [ ] Tests added
- [ ] Type hints complete
- [ ] Docstrings added
- [ ] No N+1 queries
- [ ] Sensitive data not exposed

## Documentation

### Schema Documentation

```python
@strawberry.type(description="A user in the system")
class UserType:
    """User account with profile and permissions"""

    id: strawberry.ID = strawberry.field(description="Unique user identifier")
    email: str = strawberry.field(description="User's email address")
    username: str = strawberry.field(description="Display name")

    @strawberry.field(description="User's posts, ordered by creation date")
    def posts(self) -> List[PostType]:
        """Get all posts by this user"""
        return self.post_set.all().order_by('-created_at')
```

### API Documentation

```python
# Use tools like:
# - GraphiQL for interactive exploration
# - Postman for API documentation
# - Apollo Studio for monitoring

# Enable GraphiQL in development
from strawberry_django.views import GraphQLView

urlpatterns = [
    path('graphql/', GraphQLView.as_view(
        schema=schema,
        graphiql=settings.DEBUG  # Enable in development
    )),
]
```

## Deployment

### Production Settings

```python
# settings/production.py
DEBUG = False

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# CORS for GraphQL
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
]

# Disable GraphiQL in production
STRAWBERRY_DJANGO = {
    'GRAPHIQL': False,
}

# Rate limiting
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
    }
}
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Environment Variables

```python
# Use environment variables for sensitive data
import os

SECRET_KEY = os.environ.get('SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')
REDIS_URL = os.environ.get('REDIS_URL')
```

## Common Pitfalls

### 1. Forgetting to Paginate

```python
# Bad: Can return millions of records
@strawberry.field
def users(self) -> List[UserType]:
    return User.objects.all()

# Good: Always limit results
@strawberry.field
def users(self, limit: int = 20) -> List[UserType]:
    return User.objects.all()[:limit]
```

### 2. N+1 Queries

```python
# Bad: N+1 queries
@strawberry.field
def books(self) -> List[BookType]:
    return Book.objects.all()  # Author fetched per book!

# Good: Use optimizer
schema = strawberry.Schema(
    query=Query,
    extensions=[DjangoOptimizerExtension()]
)
```

### 3. Exposing Sensitive Data

```python
# Bad: Exposes password hash
@strawberry_django.type(User)
class UserType:
    password: str  # Never expose!

# Good: Only expose safe fields
@strawberry_django.type(User)
class UserType:
    id: strawberry.ID
    email: str
    username: str
```

### 4. Missing Error Handling

```python
# Bad: Crashes on errors
@strawberry.mutation
def create_user(self, data: CreateUserInput) -> UserType:
    return User.objects.create(**data)  # May raise exceptions!

# Good: Handle errors
create_user: UserType = mutations.create(
    models.User,
    handle_django_errors=True
)
```

### 5. Synchronous Operations in Async

```python
# Bad: Blocking database call in async
async def resolver(self):
    return User.objects.all()  # Blocks!

# Good: Use sync_to_async
from asgiref.sync import sync_to_async

async def resolver(self):
    return await sync_to_async(list)(User.objects.all())
```

## See Also

- [Security Guide](security.md) - Detailed security practices
- [Performance Guide](performance.md) - Optimization strategies
- [Testing Guide](testing.md) - Comprehensive testing approaches
- [Error Handling](error-handling.md) - Error handling patterns
- [Django Best Practices](https://docs.djangoproject.com/en/stable/misc/design-philosophies/) - Django design philosophies
