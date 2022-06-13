# Frequently Asked Questions (FAQ)

## How to access Django request object in resolvers?

Request object is accessible from `info.context.request` object.

```python
def resolver(root, info: Info):
    request = info.context.request
```

## How to access current user object in resolvers?

Request object is accessible via `info.context.request.user` object.

```python
def resolver(root, info: Info):
    current_user = info.context.request.user
```
