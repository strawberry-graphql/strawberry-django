def get_group(instance):
    meta = instance.__class__._meta
    return f"strawberry-subscription-{meta.app_label}.{meta.model_name}"


def get_msg_type(instance):
    group = get_group(instance)
    return f"{group}_{instance.id}"


def get_msg(instance):
    return {"type": get_msg_type(instance)}
