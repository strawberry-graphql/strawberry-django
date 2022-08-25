# Pagination

Currently only offset and limit type of pagination are supported.

```python
@strawberry.django.type(models.Fruit, pagination=True)
class Fruit:
    name: auto
```
