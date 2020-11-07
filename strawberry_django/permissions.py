import strawberry


class ModelPermissions(strawberry.BasePermission):
    def has_permission(self, root, info, **kwargs):
        if info.context is None:
            self.message = f'Missing context object'
            return False
        request = info.context.get('request')
        if request is None:
            self.message = f'Missing request object'
            return False
        # required permission hass been added to this object by wrap_model_permission_class
        if not request.user.has_perms([self.required_permission]):
            self.message = f'User does not have {self.required_permission} permission'
            return False
        return True


def permission_class_wrapper(permission_class, model, permission_codename):
    if not issubclass(permission_class, ModelPermissions):
        return permission_class

    app_label, model_name = model._meta.app_label, model._meta.model_name
    permission_name = f'{app_label}.{permission_codename}_{model_name}'
    def _permission_class(*args, **kwargs):
        instance = permission_class(*args, **kwargs)
        # this will be checked later on in ModelPermissions class
        instance.required_permission = permission_name
        return instance
    return _permission_class
