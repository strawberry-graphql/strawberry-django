---
title: Nested Mutations and Relationships
---

# Nested Mutations and Relationships

Strawberry Django provides automatic handling for creating and updating related objects in mutations. This guide shows both the automatic approach (recommended) and manual patterns for more control.

## Automatic Nested Mutations

Strawberry Django's `mutations.create` and `mutations.update` automatically handle nested relationships for you.

### Basic Example

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
    author_id: auto
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
    create_author: Author = mutations.create(AuthorInput)
    update_author: Author = mutations.update(AuthorInput)
    delete_author: Author = mutations.delete(AuthorInput)
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
      name
    }
  }
}
```

### Many-to-Many Relationships

For many-to-many relationships, use `ListInput` to add, remove, or set related objects:

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
    tags: ListInput[strawberry.ID] | None = None
```

```python title="mutations.py"
@strawberry.type
class Mutation:
    create_article: Article = mutations.create(ArticleInput)
    update_article: Article = mutations.update(ArticleInputPartial)
```

The `ListInput` type supports three operations:

```graphql
# Set tags (replaces all existing tags)
mutation SetTags {
  updateArticle(data: { id: "1", tags: { set: ["1", "2", "3"] } }) {
    id
    tags {
      name
    }
  }
}

# Add tags (keeps existing, adds new)
mutation AddTags {
  updateArticle(data: { id: "1", tags: { add: ["4", "5"] } }) {
    id
    tags {
      name
    }
  }
}

# Remove specific tags
mutation RemoveTags {
  updateArticle(data: { id: "1", tags: { remove: ["2"] } }) {
    id
    tags {
      name
    }
  }
}
```

## Manual Nested Mutations

For more control, you can write custom mutation resolvers. This is useful when you need:

- Custom validation logic
- Complex business rules
- Non-standard relationship handling

### Creating Parent with Children

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
        data: AuthorInputWithBooks
    ) -> Author:
        # Create the author
        author = models.Author.objects.create(
            name=data.name,
            email=data.email
        )

        # Create associated books
        if data.books:
            for book_data in data.books:
                models.Book.objects.create(
                    title=book_data.title,
                    author=author,
                    published_date=book_data.published_date
                )

        # Return fresh object so relationships are loaded
        return models.Author.objects.get(pk=author.pk)
```

Usage:

```graphql
mutation CreateAuthorWithBooks {
  createAuthorWithBooks(
    data: {
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
      title
    }
  }
}
```

### Updating One-to-Many Relationships

```python title="models.py"
class Order(models.Model):
    customer_name = models.CharField(max_length=100)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_name = models.CharField(max_length=100)
    quantity = models.IntegerField()
```

```python title="types.py"
@strawberry_django.input(models.OrderItem)
class OrderItemInput:
    product_name: auto
    quantity: auto

@strawberry_django.partial(models.OrderItem)
class OrderItemInputPartial(NodeInput):
    product_name: auto
    quantity: auto

@strawberry_django.partial(models.Order)
class OrderInputPartial(NodeInput):
    customer_name: auto
    items: ListInput[OrderItemInputPartial] | None = None
```

```python title="mutations.py"
@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def update_order_with_items(
        self,
        data: OrderInputPartial
    ) -> Order:
        order = models.Order.objects.get(pk=data.id)

        # Update order fields
        if data.customer_name is not strawberry.UNSET:
            order.customer_name = data.customer_name
            order.save()

        # Handle items
        if data.items is not strawberry.UNSET and data.items is not None:
            # Add new items
            if data.items.add:
                for item_data in data.items.add:
                    models.OrderItem.objects.create(
                        order=order,
                        product_name=item_data.product_name,
                        quantity=item_data.quantity
                    )

            # Remove items
            if data.items.remove:
                item_ids = [item.id for item in data.items.remove]
                models.OrderItem.objects.filter(
                    id__in=item_ids,
                    order=order
                ).delete()

        return models.Order.objects.get(pk=order.pk)
```

### Custom Validation

```python title="mutations.py"
from django.core.exceptions import ValidationError

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    @transaction.atomic
    def create_order_with_items(
        self,
        customer_name: str,
        items: list[OrderItemInput]
    ) -> Order:
        # Validate before creating
        if not items:
            raise ValidationError({
                'items': 'At least one item is required'
            })

        # Create order
        order = models.Order.objects.create(customer_name=customer_name)

        # Create items
        for item_data in items:
            models.OrderItem.objects.create(
                order=order,
                product_name=item_data.product_name,
                quantity=item_data.quantity
            )

        return order
```

## Best Practices

1. **Use automatic mutations when possible** - They handle most cases and are less error-prone
2. **Always use `@transaction.atomic`** for manual mutations that modify multiple objects
3. **Return fresh objects** from mutations by refetching from the database
4. **Validate early** before performing database operations
5. **Use `@strawberry_django.partial`** for update mutations to support optional fields

## Common Patterns

### Conditional Updates

Only update relationships when explicitly provided:

```python
@strawberry_django.mutation(handle_django_errors=True)
def update_article(self, data: ArticleInputPartial) -> Article:
    article = models.Article.objects.get(pk=data.id)

    # Only update tags if provided (not UNSET)
    if data.tags is not strawberry.UNSET:
        if data.tags.set:
            article.tags.set(data.tags.set)
        if data.tags.add:
            article.tags.add(*data.tags.add)
        if data.tags.remove:
            article.tags.remove(*data.tags.remove)

    article.save()
    return article
```

### Many-to-Many with Through Model

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
```

```python title="mutations.py"
@strawberry_django.input(models.Enrollment)
class EnrollmentInput:
    student_id: auto
    grade: auto

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
                grade=enrollment.grade
            )

        return course
```

## See Also

- [Mutations](./mutations.md) - Basic mutation concepts
- [Error Handling](./error-handling.md) - Handling validation and errors
- [Relay](./relay.md) - Using Global IDs with NodeInput
