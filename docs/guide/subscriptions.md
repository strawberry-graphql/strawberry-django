# Subscriptions

Subscriptions are supported using the
[Strawberry Django Channels](https://strawberry.rocks/docs/integrations/channels) integration.

This guide will give you a minimal working example to get you going.
There are 3 parts to this guide:

1. Making Django compatible
2. Setup local testing
3. Creating your first subscription

## Making Django compatible

It's important to realise that Django doesnt support websockets out of the box. 
To resolve this, we can help the platform along a little.


Edit your `MyProject.asgi.py` file and replace it with the following content.
Ensure that you replace the relevant code with your setup.

```python
# MyProject.asgi.py
import os

from django.core.asgi import get_asgi_application
from strawberry.channels import GraphQLProtocolTypeRouter
 
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MyProject.settings")  # CHANGE the project name
django_asgi_app = get_asgi_application()

# Import your Strawberry schema after creating the django ASGI application
# This ensures django.setup() has been called before any ORM models are imported
# for the schema.

from .schema import schema  # CHANGE path to where you housed your schema file.
 
 
application = GraphQLProtocolTypeRouter(
    schema,
    django_application=django_asgi_app,
)
```

Also, ensure that you enable subscriptions on your AsgiGraphQLView in `MyProject.urls.py`:

```python
...

urlpatterns = [
	...
    path('graphql/', AsyncGraphQLView.as_view(
        schema=schema,
        graphiql=settings.DEBUG,
        subscriptions_enabled=True
        )
    ),
    ...
]

```

Note, django-channels allows for a lot more complexity. Here we just cover the basic framework to get 
subscriptions to run on Django with minimal effort.


## Setup local testing

The classic `./manage.py runserver` will not support subscriptions.  However, Django has daphne support out of the box to ensure that we can actually use Daphne for the runserver command. [Source](https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/daphne/)


Firstly, we need install Daphne to handle the workload, so let's install it:

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

and add your ASGI_APPLICATION setting in your settings.py

```python
# settings.py
...
ASGI_APPLICATION = 'MyProject.asgi.application'
...
```


Now you can run your test-server like as usual:

```bash
./manage.py runserver
```

## Creating your first subscription

Once you've taken care of those 2 setup steps, your first subscription is a breeze.
Go and edit your schema-file and add:

```python
from strawberry import type, subscription
import asyncio

@type
class Subscription:
    @subscription
    async def count(self, target: int = 100) -> int:
        for i in range(target):
            yield i
            await asyncio.sleep(0.5)
```

That's pretty much it for this basic start.
