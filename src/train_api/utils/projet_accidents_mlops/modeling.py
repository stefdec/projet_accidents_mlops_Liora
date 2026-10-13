"""Adaptateurs de modèle partagés entre entraînement et service MLflow."""

from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin


class ThresholdedBinaryClassifier(ClassifierMixin, BaseEstimator):
    """Expose un pipeline ajusté avec un seuil de classification explicite."""

    def __init__(self, pipeline, threshold: float = 0.5) -> None:
        self.pipeline = pipeline
        self.threshold = threshold

    @property
    def classes_(self):
        return self.pipeline.classes_

    def predict_proba(self, X):
        return self.pipeline.predict_proba(X)

    def predict(self, X):
        probabilities = self.predict_proba(X)[:, 1]
        return (probabilities >= float(self.threshold)).astype(np.int64)
