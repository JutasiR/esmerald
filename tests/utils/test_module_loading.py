import pytest

from esmerald import EsmeraldAPISettings
from esmerald.utils.module_loading import import_string


def test_import_error_module_loading():
    path = "tests"

    with pytest.raises(ImportError):
        import_string(path)


def test_attribute_error_module_loading():
    path = "tests.settings.TestSetting"

    with pytest.raises(ImportError):
        import_string(path)


def test_imports_successfully():
    path = "tests.settings.TestSettings"

    settings = import_string(path)

    assert issubclass(settings, EsmeraldAPISettings)
