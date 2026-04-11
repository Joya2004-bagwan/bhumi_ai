# Models package initialization

from .segmentation_model import SegmentationModel


# Lazy import for adapters to avoid requiring heavy dependencies at import time
def _get_yolov8_adapter():
    from .yolov8_adapter import YOLOv8Adapter
    return YOLOv8Adapter

def _get_maskrcnn_adapter():
    from .maskrcnn_adapter import MaskRCNNAdapter
    return MaskRCNNAdapter

def _get_unet_adapter():
    from .unet_adapter import UNetAdapter
    return UNetAdapter

def _get_segmentation_model_manager():
    from .segmentation_model_manager import SegmentationModelManager
    return SegmentationModelManager

__all__ = ['SegmentationModel', 'YOLOv8Adapter', 'MaskRCNNAdapter', 'UNetAdapter', 'SegmentationModelManager']


def __getattr__(name):
    _lazy = {
        'YOLOv8Adapter': _get_yolov8_adapter,
        'MaskRCNNAdapter': _get_maskrcnn_adapter,
        'UNetAdapter': _get_unet_adapter,
        'SegmentationModelManager': _get_segmentation_model_manager,
    }
    if name in _lazy:
        return _lazy[name]()
    # Allow normal submodule resolution (e.g. backend.models.yolov8_adapter)
    import importlib
    try:
        return importlib.import_module(f'.{name}', __name__)
    except ImportError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
