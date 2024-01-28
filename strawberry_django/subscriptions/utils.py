def get_group(instance):
    return f"{instance.__class__.__name__}"


def get_msg_type(instance):
    group = get_group(instance)
    return f"{group}_{instance.id}"


def get_msg(instance):
    return {"type": get_msg_type(instance)}
