### Subscriptions

Subscriptions are supported using the
[Strawberry Django Channels](https://strawberry.rocks/docs/integrations/channels) integration.

This guide will give you a minimal working example to get you going.
There are 3 parts to this guide:

1. Making Django compatible with websockets
2. Changing your habits when testing locally
2. Creating your first subscription

## Making Django compatible

It's important to realise that Django doesnt support websockets out of the box. 
So we'll need to make a few changes.


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

Note, django-channels allows for a lot more complexity. Here we just cover the basic framework to get 
subscriptions to run on Django with minimal effort.


## Changing your habits when testing locally

Traditionally you would run `./manage runserver` or some variation of that to test your app locally.
From now on - or at least when using subscriptions - you will need to run `./manage runserver_asgi

In order to use this new test-server we need to take again 3 steps.


Firstly, we need an asgi server to handle the workload, so let's install it:

```bash
pip install hypercorn
```

Secondly, we need to add `strawberry_django` to your settings.py file.

```python
INSTALLED_APPS = [
	...
    'strawberry-graphql-django'
    ...
]
``` 

And thirdly, running the new test-server will not load the static-files we need automatically.
So we'll add the following code to `MyProject.urls.py`

```python
if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from django.views.generic.base import RedirectView

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path(r'favicon\.ico',
            RedirectView.as_view(
                url=settings.STATIC_URL + 'favicon.ico', permanent=True
            )
        ),
    ]
```


Now you can run your test-server like this:

```bash
./manage.py runserver_asgi
# To see other options:
# ./manage.py runserver_asgi --help
```

Why is the test-server based on hypercorn, when you can use Daphne or Uvicorn?  We're picking hypercorn as it supports auto-reload which is great when developing and mimics the behaviour of the original runserver script.


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