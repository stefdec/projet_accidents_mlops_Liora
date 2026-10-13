import numpy as np

from projet_accidents_mlops.modeling import ThresholdedBinaryClassifier


class FakePipeline:
    classes_ = np.array([0, 1])

    def predict_proba(self, X):
        return np.array([[0.51, 0.49], [0.50, 0.50]])


def test_thresholded_classifier_uses_project_threshold() -> None:
    model = ThresholdedBinaryClassifier(FakePipeline(), threshold=0.48)

    assert model.predict([{}, {}]).tolist() == [1, 1]
    assert model.predict_proba([{}, {}]).shape == (2, 2)
