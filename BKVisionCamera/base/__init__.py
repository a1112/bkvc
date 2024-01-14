from pypattyrn.creational.singleton import Singleton


def register():
    """
    Register the name of the class
    Args:
        name: name of the class
    Returns:
    """
    model = SingCameraAll()

    def inner(cls):
        for name in cls.names:
            model.register(name, cls)
        return cls

    return inner


class SingCameraAll(metaclass=Singleton):
    def __init__(self):
        self.models = {}
        super().__init__()

    def register(self, name, class_):
        self.models[name.lower()] = class_

    def create(self, property_):
        return self.models[property_.name.lower()](property_)

    def get_camera_list(self):
        res = {}
        for key in self.models.keys():
            res[key] = self.models[key].get_model_list()
        return res
