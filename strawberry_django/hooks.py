def add_hook(field, hook_name, hooks):
    if hooks is None:
        hooks = []
    if not isinstance(hooks, (list, tuple)):
        hooks = [hooks]
    field._hooks[hook_name] = hooks

    def register_hook(func):
        field._hooks[hook_name].append(func)

    setattr(field, hook_name, register_hook)


def add(**kwargs):
    def wrapper(field):
        field._hooks = {}
        for hook_name, hooks in kwargs.items():
            add_hook(field, hook_name, hooks)

        def call_hooks(hook_name, caller):
            for hook in field._hooks[hook_name]:
                caller(hook)

        field._call_hooks = call_hooks
        return field

    return wrapper
