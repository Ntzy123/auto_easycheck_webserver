"""Tests for auto-easycheck-webserver application."""
import os
import json
import sys
import pytest
from unittest.mock import patch, MagicMock


# ---- App & Config ----

def test_app_import():
    from auto_easycheck_webserver.app import app
    assert app is not None
    assert app.secret_key is None
    assert app.debug is False


def test_main_dependencies_import():
    """确认所有主要外部依赖包均可正常导入"""
    import flask
    import waitress
    from waitress import serve
    import auto_easycheck
    import easycheck_manager
    from easycheck_manager import WebDriverManager

    assert callable(serve)
    assert hasattr(flask, "Flask")
    assert hasattr(auto_easycheck, "run")
    assert issubclass(WebDriverManager, object)


# ---- Instance Persistence ----

@pytest.fixture(autouse=True)
def _isolate_files(monkeypatch, tmp_path):
    """使用临时目录隔离所有文件副作用"""
    import auto_easycheck_webserver  # 触发 __init__.py，确保子模块已加载到 sys.modules
    app_mod = sys.modules["auto_easycheck_webserver.app"]
    cache_dir = tmp_path / "cache"
    log_dir = tmp_path / "log"
    cache_dir.mkdir()
    log_dir.mkdir()
    monkeypatch.setattr(app_mod, "instances_file",
                        str(cache_dir / "instances.json"))
    monkeypatch.setattr(app_mod, "logs_dir", str(log_dir))
    monkeypatch.setattr(app_mod, "operation_log_file",
                        str(log_dir / "main.log"))


def _reload_app_modules():
    """重新加载 app 模块以触发模块级 reset"""
    import importlib
    app_mod = sys.modules["auto_easycheck_webserver.app"]
    importlib.reload(app_mod)
    return app_mod


def test_reset_instances_file():
    app_mod = _reload_app_modules()
    data = json.load(open(app_mod.instances_file))
    assert data == {}


def test_save_and_load_instances():
    app_mod = _reload_app_modules()
    instances = {"123": {"name": "test", "url": "http://example.com"}}
    app_mod.save_instances(instances)
    loaded = app_mod.load_instances()
    assert loaded == instances


# ---- Log Utilities ----

def test_get_logs_file_missing():
    app_mod = _reload_app_modules()
    assert app_mod.get_instance_logs("nonexistent") == ["暂无日志"]


def test_get_logs_with_content():
    app_mod = _reload_app_modules()
    log_file = os.path.join(app_mod.logs_dir, "myinstance.log")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("line1\nline2\nline3\nline4\nline5\n")
    logs = app_mod.get_instance_logs("myinstance", lines=3)
    assert logs == ["line3", "line4", "line5"]


# ---- Flask Route: GET / ----

def test_index_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200


# ---- Flask Route: GET/POST /create ----

def test_create_form_returns_200(client):
    resp = client.get("/create")
    assert resp.status_code == 200


def test_create_empty_fields(client):
    resp = client.post("/create", data={"name": "", "url": ""})
    assert resp.status_code == 200
    assert b"\xe4\xb8\x8d\xe8\x83\xbd\xe4\xb8\xba\xe7\xa9\xba" in resp.data


@patch("auto_easycheck_webserver.app.threading.Thread")
def test_create_valid(mock_thread, client):
    mock_thread.return_value.is_alive.return_value = True
    resp = client.post("/create", data={"name": "test1", "url": "http://example.com"})
    assert resp.status_code == 302  # redirect to index


# ---- Flask Route: Instance Detail ----

def test_instance_detail_not_found(client):
    resp = client.get("/instance/nonexistent")
    assert resp.status_code == 302  # redirect to index


@patch("auto_easycheck_webserver.app.threading.Thread")
def test_instance_detail_found(mock_thread, client):
    mock_thread.return_value.is_alive.return_value = True
    from auto_easycheck_webserver.app import save_instances
    save_instances({"42": {"name": "dt", "url": "http://x.com"}})
    resp = client.get("/instance/42")
    assert resp.status_code == 200


# ---- Flask Route: POST /stop ----

def test_stop_not_found(client):
    resp = client.post("/stop/nonexistent")
    assert resp.status_code == 302  # redirect to index


# ---- Flask Route: GET /api/status ----

def test_api_status(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "status" in data
    assert data["status"] == "ok"


# ---- Flask Route: POST /api/status ----

def test_api_status_post_valid_id(client):
    """POST /api/status with a valid id returns the instance"""
    from auto_easycheck_webserver.app import save_instances
    save_instances({"42": {"name": "test", "url": "http://x.com"}})
    resp = client.post("/api/status", json={"id": "42"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    assert data["instance"] is not None
    assert data["instance"]["name"] == "test"


def test_api_status_post_invalid_id(client):
    """POST /api/status with an invalid id returns code 1, instance null"""
    resp = client.post("/api/status", json={"id": "nonexistent"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 1
    assert data["instance"] is None


def test_api_status_post_non_json(client):
    """POST /api/status with non-JSON body returns 400"""
    resp = client.post("/api/status", data="not json", content_type="text/plain")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "code" in data


# ---- Flask Route: POST /api/create ----

@patch("auto_easycheck_webserver.app._start_instance")
def test_api_create_valid(mock_start, client):
    """POST /api/create with valid JSON returns 201 + instance_id"""
    mock_start.return_value = ("99", {"name": "test", "url": "http://x.com"})
    resp = client.post("/api/create", json={"instance_name": "test", "easycheck_url": "http://x.com"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["code"] == 0
    assert data["success"] is True
    assert data["instance_id"] == "99"


def test_api_create_missing_instance_name(client):
    """POST /api/create without instance_name returns 400"""
    resp = client.post("/api/create", json={"easycheck_url": "http://x.com"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "instance_name" in data["msg"]


def test_api_create_missing_easycheck_url(client):
    """POST /api/create without easycheck_url returns 400"""
    resp = client.post("/api/create", json={"instance_name": "test"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "easycheck_url" in data["msg"]


def test_api_create_non_json(client):
    """POST /api/create with non-JSON body returns 400"""
    resp = client.post("/api/create", data="not json", content_type="text/plain")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "code" in data


@patch("auto_easycheck_webserver.app._start_instance")
def test_api_create_start_fails(mock_start, client):
    """POST /api/create when _start_instance fails returns 500"""
    mock_start.return_value = (None, "模拟失败")
    resp = client.post("/api/create", json={"instance_name": "test", "easycheck_url": "http://x.com"})
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["code"] == 2
    assert "模拟失败" in data["msg"]


# ---- Flask Route: POST /api/get-easycheck-url ----

@pytest.fixture
def _mock_get_easycheck_url_module(monkeypatch):
    """在 sys.modules 注入 mock 的 get_easycheck_url 模块，避免 ImportError"""
    mock_module = MagicMock()
    mock_module.get_easycheck_url = MagicMock()
    monkeypatch.setitem(sys.modules, "get_easycheck_url", mock_module)
    return mock_module.get_easycheck_url


def test_api_get_easycheck_url_valid(_mock_get_easycheck_url_module, client):
    """POST /api/get-easycheck-url with valid credentials returns 200 + easycheck_url"""
    _mock_get_easycheck_url_module.return_value = "https://easycheck.example.com/auth?token=abc"
    resp = client.post("/api/get-easycheck-url",
                       json={"mobile": "13800138000", "password": "secret"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    assert data["success"] is True
    assert data["easycheck_url"] == "https://easycheck.example.com/auth?token=abc"


def test_api_get_easycheck_url_missing_mobile(client):
    """POST /api/get-easycheck-url without mobile returns 400"""
    resp = client.post("/api/get-easycheck-url", json={"password": "secret"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "mobile" in data["msg"]


def test_api_get_easycheck_url_missing_password(client):
    """POST /api/get-easycheck-url without password returns 400"""
    resp = client.post("/api/get-easycheck-url", json={"mobile": "13800138000"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "password" in data["msg"]


def test_api_get_easycheck_url_non_json(client):
    """POST /api/get-easycheck-url with non-JSON body returns 400"""
    resp = client.post("/api/get-easycheck-url", data="not json", content_type="text/plain")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "code" in data


def test_api_get_easycheck_url_exception(_mock_get_easycheck_url_module, client):
    """POST /api/get-easycheck-url when get_easycheck_url raises an exception returns 500"""
    _mock_get_easycheck_url_module.side_effect = Exception("网络错误")
    resp = client.post("/api/get-easycheck-url",
                       json={"mobile": "13800138000", "password": "secret"})
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["code"] == 2
    assert "网络错误" in data["msg"]


@pytest.fixture
def client():
    from auto_easycheck_webserver.app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
