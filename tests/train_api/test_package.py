import src.train_api as train_api


def test_package_exposes_a_non_empty_version() -> None:
    assert isinstance(train_api.__version__, str)
    assert train_api.__version__
