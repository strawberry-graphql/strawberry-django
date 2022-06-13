# Pagination

Currently only offset and limit type of pagination is supported

```python
@strawberry_django.type(models.Fruit, pagination=True)
class Fruit:
    name: auto
```
