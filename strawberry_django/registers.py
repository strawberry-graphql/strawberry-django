class TypeRegister:
    def __init__(self):
        self.generic = {}
        self.types = {}
        self.inputs = {}

    # key can be field name, django model field or django model
    def register(self, key, type=None):
        django_model = getattr(key, '_django_model', None)
        if type:
            self.add(key, type)
            return type

        if django_model:
            key, type = django_model, key
            self.add(key, type)
            return type

        def wrapper(type):
            self.add(key, type)
            return type
        return wrapper

    def add(self, key, type):
        if hasattr(type, '_type_definition'):
            if type._type_definition.is_input:
                self.inputs[key] = type
            else:
                self.types[key] = type
        else:
            self.generic[key] = type

    def get(self, key, is_input, default=None):
        if is_input:
            type = self.inputs.get(key, default)
        else:
            type = self.types.get(key, default)
        if type is default:
            type = self.generic.get(key, default)
        return type
