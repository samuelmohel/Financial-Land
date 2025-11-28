import requests
from unittest.mock import patch, Mock
from app_streamlit import find_reachable_host, check_hosts_status
from config import settings


def make_response(status_code=200):
    mock_resp = Mock()
    mock_resp.status_code = status_code
    return mock_resp


def test_find_reachable_host_returns_first_success():
    hosts = ["localhost", "127.0.0.1"]
    # Mock requests.get so the first raises (connection error) and second returns 200
    def side_effect(url, timeout):
        if "localhost" in url:
            raise requests.RequestException("Conn error")
        return make_response(200)

    with patch("requests.get", side_effect=side_effect):
        detected = find_reachable_host(hosts, settings.PORT)
        assert detected == "127.0.0.1"


def test_check_hosts_status_all_bad():
    hosts = ["a", "b"]
    with patch("requests.get", side_effect=requests.RequestException()):
        status = check_hosts_status(hosts, settings.PORT)
        assert all([not s["ok"] for s in status])
