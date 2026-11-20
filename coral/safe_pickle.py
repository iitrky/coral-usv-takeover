"""Restricted unpickler: only NumPy array reconstruction is allowed (no arbitrary code)."""
import pickle
import numpy as np

_ALLOWED = {("numpy", "ndarray"), ("numpy", "dtype"), ("numpy.core.multiarray", "_reconstruct"),
            ("numpy._core.multiarray", "_reconstruct")}


class _Safe(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in _ALLOWED:
            if name == "_reconstruct":
                return np.core.multiarray._reconstruct if hasattr(np, "core") else np._core.multiarray._reconstruct
            return getattr(np, name)
        raise pickle.UnpicklingError(f"blocked global {module}.{name}")


def load(path):
    with open(path, "rb") as f:
        return _Safe(f, encoding="latin1").load()
