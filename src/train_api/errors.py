"""Domain errors raised by the train_api workflow."""


class TrainingApiError(Exception):
    """Base exception for errors that have a stable training meaning."""


class ConfigurationError(TrainingApiError):
    """Runtime configuration is unsafe or unusable."""


class DatasetNotFound(TrainingApiError):
    """A required configured dataset is absent."""


class DatasetInvalid(TrainingApiError):
    """A dataset reference does not respect the training contract."""


class TrainingConflict(TrainingApiError):
    """A training request conflicts with persisted or active training state."""


class TrainingFailed(TrainingApiError):
    """Training could not complete successfully."""


class MlflowUnavailable(TrainingApiError):
    """MLflow cannot provide a required tracking or registry operation."""


class StateStoreError(TrainingApiError):
    """Persisted idempotence state is malformed or cannot be used safely."""
