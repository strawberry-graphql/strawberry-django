# Frequently Asked Questions (FAQ)

## How to access Django request object in resolvers?

The request object is accessible via the `info.context.request` object.

```python
def resolver(root, info: Info):
    request = info.context.request
```

## How to access the current user object in resolvers?

The current user object is accessible via the `info.context.request.user` object.

```python
def resolver(root, info: Info):
    current_user = info.context.request.user
```
