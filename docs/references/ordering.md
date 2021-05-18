# Ordering

> NOTE: this API may still change

```python
@strawberry_django.ordering.order(models.Color)
class ColorOrder:
    name: auto

@strawberry_django.ordering.order(models.Fruit)
class FruitOrder:
    name: auto
    color: ColorOrder
```
