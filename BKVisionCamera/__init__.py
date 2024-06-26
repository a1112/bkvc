from .base import SingCameraAll
from .base.property import BaseProperty, CaptureModel
from .areascancamera.hikvision import HikCamera
from .d3cancamera.SICK.sick_camera import SickCamera


def crate_capter(property_) -> CaptureModel:
    property_ = createProperty(property_)
    capter = SingCameraAll()
    return capter.create(property_)


def get_camera_list():
    capters = SingCameraAll()
    return capters.get_camera_list()


def createProperty(yaml_path):
    if isinstance(yaml_path, str):
        return BaseProperty(yaml_path)
    return yaml_path
