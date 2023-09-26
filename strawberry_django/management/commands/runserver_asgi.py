from django.core.management.commands.runserver import autoreload
from django.core.management.commands.runserver import Command as WsgiCommand
from django.core.asgi import get_asgi_application
from hypercorn.config import Config
from hypercorn.asyncio import serve
import os
import asyncio


class Command(WsgiCommand):
    # Why hypercorn?  Because it supports auto-reload.
    help = "Starts an ASGI web server called hypercorn for development."
    # server_cls = ASGIServer

    def add_arguments(self, parser):
        parser.add_argument(
            "addrport", nargs="?", help="Optional port number, or ipaddr:port"
        )
        parser.add_argument(
            "--ipv6",
            "-6",
            action="store_true",
            dest="use_ipv6",
            help="Tells Django to use an IPv6 address.",
        )

        parser.add_argument(
            "--noreload",
            action="store_false",
            dest="use_reloader",
            help="Tells Django to NOT use the auto-reloader.",
        )

        parser.add_argument(
            "--skip-checks",
            action="store_true",
            help="Skip system checks.",
        )

    def execute(self, *args, **options):
        if options["no_color"]:
            os.environ["DJANGO_COLORS"] = "nocolor"
        super().execute(*args, **options)

    def get_handler(self, *args, **options):
        """Return the default WSGI handler for the runner."""
        return get_asgi_application()

    def run(self, **options):
        """Run the server, using the autoreloader if needed."""
        self.inner_run(None, **options)

    def inner_run(self, *args, **options):
        # If an exception was silenced in ManagementUtility.execute in order
        # to be raised in the child process, raise it now.
        autoreload.raise_last_exception()

        # 'shutdown_message' is a stealth option.
        shutdown_message = options.get("shutdown_message", "")


        # Use reload?
        # FIXME: use_reloader doesnt seem to be working.
        use_reloader = options["use_reloader"]

        if not options["skip_checks"]:
            self.stdout.write("Performing system checks...\n\n")
            self.check(display_num_errors=True)
        # Need to check migrations here, so can't use the
        # requires_migrations_check attribute.
        self.check_migrations()

        try:
            handler = self.get_handler(*args, **options)

            config = Config()
            config.bind = [f"{self.addr}:{self.port}"]
            config.use_reloader = use_reloader

            asyncio.run(serve(handler, config))
        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write(shutdown_message)
            sys.exit(0)



