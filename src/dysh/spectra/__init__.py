"""Classes and functions for managing and processing spectra."""

from importlib import import_module

__all__ = ["core", "scan", "spectrum", "Spectrum", "average_spectra"]

_EXPORTS = {
    "Spectrum": (".spectrum", "Spectrum"),
    "average_spectra": (".spectrum", "average_spectra"),
}

_MODULE_EXPORTS = {
    "core": ".core",
    "scan": ".scan",
    "spectrum": ".spectrum",
}


def __getattr__(name):
    if name in _EXPORTS:
        module_name, attr_name = _EXPORTS[name]
        module = import_module(module_name, __name__)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    if name in _MODULE_EXPORTS:
        module = import_module(_MODULE_EXPORTS[name], __name__)
        globals()[name] = module
        return module
    # Fall through to core module for backwards-compatible attribute access
    _core = import_module(".core", __name__)
    if hasattr(_core, name):
        value = getattr(_core, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
