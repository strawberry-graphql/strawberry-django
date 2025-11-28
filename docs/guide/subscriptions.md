---
title: Subscriptions
---

# Subscriptions

Subscriptions are supported using the
[Strawberry Django Channels](https://strawberry.rocks/docs/integrations/channels) integration.

This guide will give you a minimal working example to get you going.
There are 3 parts to this guide:

1. Making Django compatible
2. Setup local testing
3. Creating your first subscription

## Making Django compatible

It's important to realise that Django doesn't support websockets out of the box.
To resolve this, we can help the platform along a little.

This implementation is based on Django Channels - this means that should you wish - there is a lot more websockets fun to be had. If you're interested, head over to [Django Channels](https://channels.readthedocs.io).

To add the base compatibility, go to your `MyProject.asgi.py` file and replace it with the following content.
Ensure that you replace the relevant code with your setup.

```python
# MyProject.asgi.py
import os

from django.core.asgi import get_asgi_application
from strawberry_django.routers import AuthGraphQLProtocolTypeRouter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MyProject.settings")  # CHANGE the project name
django_asgi_app = get_asgi_application()

# Import your Strawberry schema after creating the django ASGI application
# This ensures django.setup() has been called before any ORM models are imported
# for the schema.

from .schema import schema  # CHANGE path to where you housed your schema file.
application = AuthGraphQLProtocolTypeRouter(
    schema,
    django_application=django_asgi_app,
)
```

Note, django-channels allows for a lot more complexity. Here we merely cover the basic framework to get subscriptions to run on Django with minimal effort. Should you be interested in discovering the far more advanced capabilities of Django channels, head over to [channels docs](https://channels.readthedocs.io)

## Setup local testing

The classic `./manage.py runserver` will not support subscriptions as it runs on WSGI mode. However, Django has ASGI server support out of the box through Daphne, which will override the runserver command to support our desired ASGI support.

There are other asgi servers available, such as Uvicorn and Hypercorn. For the sake of simplicity we'll use Daphne as it comes with the runserver override. [Django Docs](https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/daphne/) This shouldn't stop you from using any of the other ASGI flavours in production or local testing like Uvicorn or Hypercorn

To get started: Firstly, we need install Daphne to handle the workload, so let's install it:

```bash
pip install daphne
```

Secondly, we need to add `daphne` to your settings.py file before 'django.contrib.staticfiles'

```python
INSTALLED_APPS = [
	...
    'daphne',
    'django.contrib.staticfiles',
    ...
]
```

and add your `ASGI_APPLICATION` setting in your settings.py

```python
# settings.py
...
ASGI_APPLICATION = 'MyProject.asgi.application'
...
```

Now you can run your test-server like as usual, but with ASGI support:

```bash
./manage.py runserver
```

## Creating your first subscription

Once you've taken care of those 2 setup steps, your first subscription is a breeze.
Go and edit your schema-file and add:

```python
import asyncio
import strawberry

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def count(self, target: int = 100) -> int:
        for i in range(target):
            yield i
            await asyncio.sleep(0.5)
```

That's pretty much it for this basic start.
See for yourself by running your test server `./manage.py runserver` and opening `http://127.0.0.1:8000/graphql/` in your browser. Now run:

```graphql
subscription {
  count(target: 10)
}
```

You should see something like (where the count changes every .5s to a max of 9)

```json
{
  "data": {
    "count": 9
  }
}
```
