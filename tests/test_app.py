"""Tests for easycheck-webserver application."""


def test_imports():
    """Verify core modules can be imported."""
    from easycheck_webserver.app import app
    assert app is not None


def test_app_config():
    """Verify Flask app is properly configured."""
    from easycheck_webserver.app import app
    assert app.secret_key is None  # default
    assert app.debug is False  # default, overridden in main()


def test_webdriver_manager_import():
    """Verify WebDriverManager can be imported."""
    from easycheck_webserver.webdriver_manager import WebDriverManager
    wd = WebDriverManager()
    assert wd is not None
    assert hasattr(wd, "start")
    assert hasattr(wd, "set_permanent_path")
    assert hasattr(wd, "download_edgedriver")
