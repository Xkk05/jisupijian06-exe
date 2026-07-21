import hashlib
from urllib.parse import parse_qs, urlparse

class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_get_machine_code_hashes_available_hardware_parts(monkeypatch):
    from utils import auth_code_service

    monkeypatch.setattr(auth_code_service, "get_cpu_info", lambda: "cpu-1")
    monkeypatch.setattr(auth_code_service, "get_mac_address", lambda: "AA-BB-CC")
    monkeypatch.setattr(auth_code_service, "get_motherboard_serial", lambda: "board-1")

    expected = hashlib.sha256("cpu-1|AA-BB-CC|board-1".encode("utf-8")).hexdigest()

    assert auth_code_service.get_machine_code() == expected


def test_build_auth_code_url_appends_device_and_software_query():
    from utils.auth_code_service import build_auth_code_url

    url = build_auth_code_url(
        "https://auth-code.kunqiongai.com/web/auth/index?source=desktop",
        device_id="machine-1",
        soft_number="10039",
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "auth-code.kunqiongai.com"
    assert query["source"] == ["desktop"]
    assert query["device_id"] == ["machine-1"]
    assert query["software_code"] == ["10039"]


def test_check_need_auth_code_returns_authorized_when_api_says_no_code_needed(temp_dir):
    from utils.auth_code_service import AuthCodeService

    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        captured["timeout"] = timeout
        return FakeResponse({"code": 1, "msg": "成功", "data": {"is_need_auth_code": 0}})

    service = AuthCodeService(
        data_dir_provider=lambda: temp_dir,
        machine_code_provider=lambda: "machine-1",
        post_func=fake_post,
    )

    result = service.check_need_auth_code()

    assert result.success is True
    assert result.need_auth_code is False
    assert result.device_id == "machine-1"
    assert captured["url"].endswith("/soft_desktop/check_get_auth_code")
    assert captured["data"] == {"device_id": "machine-1", "soft_number": "10039"}
    assert captured["timeout"] == 10


def test_check_need_auth_code_returns_url_when_code_is_required(temp_dir):
    from utils.auth_code_service import AuthCodeService

    def fake_post(url, data=None, timeout=None):
        return FakeResponse(
            {
                "code": 1,
                "msg": "成功",
                "data": {
                    "is_need_auth_code": 1,
                    "auth_code_url": "https://auth-code.kunqiongai.com/web/auth/index",
                },
            }
        )

    service = AuthCodeService(
        data_dir_provider=lambda: temp_dir,
        machine_code_provider=lambda: "machine-1",
        post_func=fake_post,
    )

    result = service.check_need_auth_code()

    assert result.success is True
    assert result.need_auth_code is True
    assert result.auth_code_url == "https://auth-code.kunqiongai.com/web/auth/index"
    assert result.device_id == "machine-1"


def test_verify_auth_code_caches_code_when_valid(temp_dir):
    from utils.auth_code_service import AuthCodeService

    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["data"] = data
        return FakeResponse(
            {
                "code": 1,
                "msg": "授权码有效",
                "data": {"auth_code_status": 1},
            }
        )

    service = AuthCodeService(
        data_dir_provider=lambda: temp_dir,
        machine_code_provider=lambda: "machine-1",
        post_func=fake_post,
    )

    result = service.verify_auth_code("ABCD1234")

    assert result.success is True
    assert result.is_valid is True
    assert result.message == "授权码有效"
    assert service.get_stored_auth_code() == "ABCD1234"
    assert captured["data"] == {
        "device_id": "machine-1",
        "soft_number": "10039",
        "auth_code": "ABCD1234",
    }


def test_validate_stored_auth_code_clears_invalid_code(temp_dir):
    from utils.auth_code_service import AuthCodeService

    def fake_post(url, data=None, timeout=None):
        return FakeResponse(
            {
                "code": 1,
                "msg": "授权码无效",
                "data": {"auth_code_status": 0},
            }
        )

    service = AuthCodeService(
        data_dir_provider=lambda: temp_dir,
        machine_code_provider=lambda: "machine-1",
        post_func=fake_post,
    )
    service.store_auth_code("EXPIRED")

    result = service.validate_stored_auth_code()

    assert result.success is True
    assert result.is_valid is False
    assert service.get_stored_auth_code() is None


def test_open_get_auth_code_page_uses_returned_url_and_soft_number(temp_dir):
    from utils.auth_code_service import AuthCodeService

    opened = []
    service = AuthCodeService(
        data_dir_provider=lambda: temp_dir,
        machine_code_provider=lambda: "machine-1",
        opener=opened.append,
    )

    service.open_get_auth_code_page("https://auth-code.kunqiongai.com/web/auth/index")

    parsed = urlparse(opened[0])
    query = parse_qs(parsed.query)
    assert query["device_id"] == ["machine-1"]
    assert query["software_code"] == ["10039"]
