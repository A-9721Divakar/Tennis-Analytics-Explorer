import pytest
import requests

from src.api_client import SportradarClient, SportradarError


class FakeResponse:
    def __init__(self, status=200, payload=None, headers=None, text=""):
        self.status_code, self._payload, self.headers, self.text = status, payload, headers or {}, text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_client(responses, tmp_path, **kw):
    return SportradarClient("SECRET", request_delay=0, raw_dir=tmp_path, session=FakeSession(responses), **kw)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("src.api_client.time.sleep", lambda *_: None)


def test_requires_api_key(tmp_path):
    with pytest.raises(SportradarError):
        SportradarClient("", raw_dir=tmp_path)


def test_builds_expected_url_and_caches_json(tmp_path):
    client = make_client([FakeResponse(payload={"competitions": []})], tmp_path)
    assert client.fetch("competitions") == {"competitions": []}
    url, params = client.session.calls[0]
    assert url == "https://api.sportradar.com/tennis/trial/v3/en/competitions.json"
    assert params == {"api_key": "SECRET"}
    offline = make_client([], tmp_path)
    assert offline.fetch("competitions", use_cache=True) == {"competitions": []}


def test_retries_on_429_then_succeeds(tmp_path):
    client = make_client([FakeResponse(429), FakeResponse(503), FakeResponse(payload={"ok": 1})], tmp_path)
    assert client.fetch("complexes") == {"ok": 1}
    assert len(client.session.calls) == 3


def test_retries_network_errors_and_redacts_key(tmp_path):
    err = requests.ConnectionError("boom SECRET")
    client = make_client([err, err], tmp_path, max_retries=2)
    with pytest.raises(SportradarError) as exc:
        client.fetch("rankings")
    assert "SECRET" not in str(exc.value)


def test_auth_error_is_explained(tmp_path):
    client = make_client([FakeResponse(403, text="forbidden")], tmp_path)
    with pytest.raises(SportradarError, match="API key"):
        client.fetch("competitions")


def test_unknown_dataset(tmp_path):
    with pytest.raises(SportradarError):
        make_client([], tmp_path).fetch("nope")
