---
title: Nested Mutations and Relationships
---

# Nested Mutations and Relationships

Working with related data in mutations is a common requirement in GraphQL APIs. Strawberry Django provides powerful tools for handling nested objects and relationships in create, update, and delete operations.

## Understanding Relationship Input Types

Strawberry Django provides specialized input types for handling relationships:

- `OneToOneInput`: For one-to-one relationships
- `OneToManyInput`: For reverse foreign key relationships (one parent, many children)
- `ManyToOneInput`: For foreign key relationships (many children, one parent)
- `ManyToManyInput`: For many-to-many relationships
- `ListInput[T]`: Generic list input with `add`, `remove`, and `set` operations

## Simple Foreign Key Relationships

### Creating Objects with Foreign Keys

```python title="models.py"
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    published_date = models.DateField()
```

```python title="types.py"
import strawberry_django
from strawberry import auto

@strawberry_django.type(models.Author)
class Author:
    id: auto
    name: auto
    email: auto
    books: list["Book"]

@strawberry_django.type(models.Book)
class Book:
    id: auto
    title: auto
    author: Author
    published_date: auto

@strawberry_django.input(models.Book)
class BookInput:
    title: auto
    author_id: auto  # Reference existing author by ID
    published_date: auto

@strawberry_django.input(models.Author)
class AuthorInput:
    name: auto
    email: auto
```

```python title="mutations.py"
import strawberry
from strawberry_django import mutations

@strawberry.type
class Mutation:
    create_book: Book = mutations.create(BookInput)
```

Usage:

```graphql
mutation CreateBook {
  createBook(
    data: {
      title: "Django for Beginners"
      authorId: "1"
      publishedDate: "2024-01-01"
    }
  ) {
    id
    title
    author {
      id
      name
    }
  }
}
```

## Nested Object Creation

### Creating Parent and Child Together

```python title="types.py"
@strawberry_django.input(models.Author)
class AuthorInputWithBooks:
    name: auto
    email: auto
    books: list[BookInput] | None = None
```

```python title="mutations.py"
from typing import cast
from django.db import transaction

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def create_author_with_books(
        self,
        info,
        author: AuthorInputWithBooks
    ) -> Author:
        # Create the author
        author_obj = models.Author.objects.create(
            name=author.name,
            email=author.email
        )

        # Create associated books if provided
        if author.books:
            for book_input in author.books:
                models.Book.objects.create(
                    title=book_input.title,
                    author=author_obj,
                    published_date=book_input.published_date
                )

        return cast(Author, author_obj)
```

Usage:

```graphql
mutation CreateAuthorWithBooks {
  createAuthorWithBooks(
    author: {
      name: "Jane Smith"
      email: "jane@example.com"
      books: [
        { title: "Book One", publishedDate: "2024-01-01" }
        { title: "Book Two", publishedDate: "2024-06-01" }
      ]
    }
  ) {
    id
    name
    books {
      id
      title
    }
  }
}
```

## Many-to-Many Relationships

### Using ListInput for M2M Operations

```python title="models.py"
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    tags = models.ManyToManyField(Tag, related_name="articles")
```

```python title="types.py"
from strawberry_django import ListInput, NodeInput

@strawberry_django.type(models.Article)
class Article:
    id: auto
    title: auto
    content: auto
    tags: list["Tag"]

@strawberry_django.type(models.Tag)
class Tag:
    id: auto
    name: auto

@strawberry_django.input(models.Article)
class ArticleInput:
    title: auto
    content: auto
    tags: ListInput[strawberry.ID] | None = None

@strawberry_django.partial(models.Article)
class ArticleInputPartial(NodeInput):
    title: auto
    content: auto
    tags: ListInput[strawberry.ID] | None = None
```

```python title="mutations.py"
@strawberry.type
class Mutation:
    create_article: Article = mutations.create(ArticleInput)
    update_article: Article = mutations.update(ArticleInputPartial)
```

### M2M Operations

The `ListInput` type supports three operations:

1. **`set`**: Replace all relationships with the provided list
2. **`add`**: Add new relationships while keeping existing ones
3. **`remove`**: Remove specific relationships

```graphql
# Set tags (replaces all existing tags)
mutation SetTags {
  updateArticle(data: { id: "1", tags: { set: ["1", "2", "3"] } }) {
    id
    tags {
      id
      name
    }
  }
}

# Add tags (keeps existing, adds new)
mutation AddTags {
  updateArticle(data: { id: "1", tags: { add: ["4", "5"] } }) {
    id
    tags {
      id
      name
    }
  }
}

# Remove specific tags
mutation RemoveTags {
  updateArticle(data: { id: "1", tags: { remove: ["2", "3"] } }) {
    id
    tags {
      id
      name
    }
  }
}

# Combine operations
mutation ManageTags {
  updateArticle(data: { id: "1", tags: { add: ["6", "7"], remove: ["1"] } }) {
    id
    tags {
      id
      name
    }
  }
}
```

## Reverse Foreign Key Relationships (One-to-Many)

### Updating Child Objects from Parent

```python title="models.py"
class Order(models.Model):
    customer_name = models.CharField(max_length=100)
    order_date = models.DateField()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
```

```python title="types.py"
@strawberry_django.input(models.OrderItem)
class OrderItemInput:
    product_name: auto
    quantity: auto
    price: auto

@strawberry_django.partial(models.OrderItem)
class OrderItemInputPartial(NodeInput):
    product_name: auto
    quantity: auto
    price: auto

@strawberry_django.partial(models.Order)
class OrderInputPartial(NodeInput):
    customer_name: auto
    items: ListInput[OrderItemInputPartial] | None = None
```

```python title="mutations.py"
from decimal import Decimal
from typing import cast
from django.db import transaction

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def update_order_with_items(
        self,
        info,
        data: OrderInputPartial
    ) -> Order:
        # Get the order
        order = models.Order.objects.get(pk=data.id)

        # Update order fields
        if data.customer_name is not strawberry.UNSET:
            order.customer_name = data.customer_name

        # Handle items if provided
        if data.items is not strawberry.UNSET and data.items is not None:
            # Set operation - replace all items
            if data.items.set is not None:
                order.items.all().delete()
                for item_data in data.items.set:
                    if isinstance(item_data, NodeInput):
                        # Update existing item
                        item = models.OrderItem.objects.get(pk=item_data.id)
                        if item_data.product_name is not strawberry.UNSET:
                            item.product_name = item_data.product_name
                        if item_data.quantity is not strawberry.UNSET:
                            item.quantity = item_data.quantity
                        if item_data.price is not strawberry.UNSET:
                            item.price = item_data.price
                        item.save()
                    else:
                        # Create new item
                        models.OrderItem.objects.create(
                            order=order,
                            product_name=item_data.product_name,
                            quantity=item_data.quantity,
                            price=item_data.price
                        )

            # Add operation - add new items
            if data.items.add is not None:
                for item_data in data.items.add:
                    models.OrderItem.objects.create(
                        order=order,
                        product_name=item_data.product_name,
                        quantity=item_data.quantity,
                        price=item_data.price
                    )

            # Remove operation - delete specific items
            if data.items.remove is not None:
                item_ids = [item.id for item in data.items.remove]
                models.OrderItem.objects.filter(
                    id__in=item_ids,
                    order=order
                ).delete()

        order.save()
        return cast(Order, order)
```

## Using NodeInput for Relay-Style IDs

When using the [Relay integration](./relay.md), use `NodeInput` for referencing existing objects:

```python title="types.py"
from strawberry.relay import Node
from strawberry_django import NodeInput

@strawberry_django.type(models.Article)
class Article(Node):
    title: auto
    content: auto
    tags: list["Tag"]

@strawberry_django.partial(models.Article)
class ArticleInputPartial(NodeInput):
    title: auto
    tags: ListInput[NodeInput] | None = None
```

```graphql
mutation UpdateArticle {
  updateArticle(
    data: {
      id: "QXJ0aWNsZTox" # Global ID
      tags: { set: [{ id: "VGFnOjE=" }, { id: "VGFnOjI=" }] }
    }
  ) {
    id
    title
    tags {
      id
      name
    }
  }
}
```

## Handling Nested Validation

### Validating Related Objects

```python title="mutations.py"
from django.core.exceptions import ValidationError

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def create_order_with_items(
        self,
        info,
        customer_name: str,
        items: list[OrderItemInput]
    ) -> Order:
        # Validate that items list is not empty
        if not items:
            raise ValidationError({
                'items': 'At least one item is required'
            })

        # Validate total price
        total = sum(Decimal(item.price) * item.quantity for item in items)
        if total <= 0:
            raise ValidationError({
                'items': 'Total order amount must be greater than zero'
            })

        # Create order
        order = models.Order.objects.create(
            customer_name=customer_name,
            order_date=date.today()
        )

        # Create items
        for item_input in items:
            models.OrderItem.objects.create(
                order=order,
                product_name=item_input.product_name,
                quantity=item_input.quantity,
                price=item_input.price
            )

        return cast(Order, order)
```

## Atomic Operations with Transactions

Always use database transactions for complex nested mutations:

```python title="mutations.py"
from django.db import transaction

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic  # Ensures all-or-nothing execution
    def create_complete_blog_post(
        self,
        title: str,
        content: str,
        tags: list[str],
        author_id: strawberry.ID
    ) -> BlogPost:
        # Create the post
        post = models.BlogPost.objects.create(
            title=title,
            content=content,
            author_id=author_id
        )

        # Create or get tags
        tag_objects = []
        for tag_name in tags:
            tag, _ = models.Tag.objects.get_or_create(name=tag_name)
            tag_objects.append(tag)

        # Assign tags
        post.tags.set(tag_objects)

        # If any error occurs, everything will be rolled back
        return cast(BlogPost, post)
```

## Optimizing Nested Queries

When returning nested data from mutations, ensure the [Query Optimizer](./optimizer.md) can work:

```python title="mutations.py"
@strawberry.type
class Mutation:
    @strawberry_django.mutation
    def update_author(self, data: AuthorInputPartial) -> Author:
        author = models.Author.objects.get(pk=data.id)

        # Update author...
        author.save()

        # Return optimized query - the optimizer will handle prefetching books
        # Use select_subclasses() if using polymorphic models
        return models.Author.objects.get(pk=author.pk)
```

## Common Patterns

### Pattern 1: Conditional Relationship Updates

```python
@strawberry_django.mutation(handle_django_errors=True)
def update_article(self, data: ArticleInputPartial) -> Article:
    article = models.Article.objects.get(pk=data.id)

    # Only update tags if explicitly provided
    if data.tags is not strawberry.UNSET:
        if data.tags.set is not None:
            article.tags.set(data.tags.set)
        if data.tags.add is not None:
            article.tags.add(*data.tags.add)
        if data.tags.remove is not None:
            article.tags.remove(*data.tags.remove)

    article.save()
    return article
```

### Pattern 2: Bulk Operations

```python
@strawberry_django.mutation(handle_django_errors=True)
@transaction.atomic
def bulk_assign_tags(
    self,
    article_ids: list[strawberry.ID],
    tag_ids: list[strawberry.ID]
) -> list[Article]:
    articles = models.Article.objects.filter(id__in=article_ids)
    tags = models.Tag.objects.filter(id__in=tag_ids)

    for article in articles:
        article.tags.add(*tags)

    return list(articles)
```

### Pattern 3: Creating with Through Model

For M2M relationships with extra fields:

```python title="models.py"
class Student(models.Model):
    name = models.CharField(max_length=100)

class Course(models.Model):
    name = models.CharField(max_length=100)
    students = models.ManyToManyField(Student, through='Enrollment')

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    grade = models.CharField(max_length=2)
    enrollment_date = models.DateField()
```

```python title="mutations.py"
@strawberry_django.input(models.Enrollment)
class EnrollmentInput:
    student_id: auto
    grade: auto
    enrollment_date: auto

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def enroll_students(
        self,
        course_id: strawberry.ID,
        enrollments: list[EnrollmentInput]
    ) -> Course:
        course = models.Course.objects.get(pk=course_id)

        for enrollment in enrollments:
            models.Enrollment.objects.create(
                course=course,
                student_id=enrollment.student_id,
                grade=enrollment.grade,
                enrollment_date=enrollment.enrollment_date
            )

        return cast(Course, course)
```

## Known Issues and Workarounds

### Issue: Related Objects Not Appearing in Mutation Response

**Problem**: After creating related objects in a mutation, they don't appear in the response.

**Solution**: Refresh the object or fetch it again:

```python
@strawberry_django.mutation
@transaction.atomic
def create_author_with_books(self, data: AuthorInput) -> Author:
    author = models.Author.objects.create(name=data.name)

    for book_data in data.books:
        models.Book.objects.create(author=author, **book_data)

    # Refresh to clear cached relationships
    author.refresh_from_db()

    # Or fetch again (better for optimizer)
    return models.Author.objects.get(pk=author.pk)
```

### Issue: Polymorphic Models in ListInput

**Problem**: When using model inheritance with `ListInput[NodeInput]`, concrete types aren't properly matched.

**Workaround**: Use the abstract base model for lookups or ensure you're using `InheritanceManager` with `select_subclasses()`.

See [Optimizer - Polymorphic Models](./optimizer.md#optimizing-polymorphic-queries) for more details.

## Best Practices

1. **Always use transactions** for operations that modify multiple objects
2. **Validate early** before performing database operations
3. **Use partial inputs** for update mutations to support optional fields
4. **Return fresh objects** to ensure relationships are properly loaded
5. **Document expected behavior** in mutation docstrings
6. **Handle UNSET vs None** appropriately in partial updates
7. **Use atomic operations** for M2M relationships when possible
8. **Test edge cases** like empty lists, duplicate IDs, and non-existent references

## Troubleshooting

### Relationships not updating

Check that you're using the correct input type (`ListInput`, `NodeInput`, etc.) and that the field name matches the model's relation name.

### Validation errors unclear

Use field-specific validation errors:

```python
raise ValidationError({
    'items.0.price': 'Price must be positive',
    'items.1.quantity': 'Quantity must be greater than zero'
})
```

### Transaction rollback issues

Ensure `@transaction.atomic` is applied and check for any try/except blocks that might be swallowing errors.

## See Also

- [Mutations](./mutations.md) - Basic mutation concepts
- [Error Handling](./error-handling.md) - Handling validation and errors
- [Relay](./relay.md) - Using Global IDs with NodeInput
- [Optimizer](./optimizer.md) - Optimizing nested queries
