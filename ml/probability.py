"""把 sklearn 概率列映射至固定的 49 个号码，兼容训练时缺少类别。"""

import numpy as np

from ml.data import NUM_CLASSES


def predict_proba_49(model, x: np.ndarray) -> np.ndarray:
    proba = np.asarray(model.predict_proba(x), dtype=float)
    classes = np.asarray(model.classes_)
    if (
        classes.ndim != 1
        or not np.issubdtype(classes.dtype, np.integer)
        or np.any((classes < 0) | (classes >= NUM_CLASSES))
        or len(np.unique(classes)) != len(classes)
        or proba.shape != (len(x), len(classes))
    ):
        raise ValueError("模型类别必须是 0..48 的唯一整数，且与概率列一一对应")
    if not np.isfinite(proba).all() or np.any(proba < 0) or not np.allclose(proba.sum(axis=1), 1):
        raise ValueError("模型输出了无效概率")
    aligned = np.zeros((len(x), NUM_CLASSES), dtype=float)
    aligned[:, classes] = proba
    return aligned
