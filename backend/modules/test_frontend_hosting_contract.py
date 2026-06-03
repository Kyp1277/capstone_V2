from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_frontend_defaults_to_same_origin_when_hosted():
    state_js = (PROJECT_ROOT / "js" / "state.js").read_text(encoding="utf-8")
    assert "export function getDefaultApiBaseUrl" in state_js
    assert 'return isLocalHost ? "http://127.0.0.1:5000" : locationLike.origin;' in state_js


def test_autocomplete_uses_configured_api_base_url():
    http_js = (PROJECT_ROOT / "js" / "http.js").read_text(encoding="utf-8")
    events_js = (PROJECT_ROOT / "js" / "events.js").read_text(encoding="utf-8")
    assert 'import { API_BASE_URL, state } from "./state.js";' in http_js
    assert "new URL(path, API_BASE_URL)" in http_js
    assert "fetch(requestUrl, init)" in http_js
    assert 'import { http } from "./http.js";' in events_js
    assert 'http.get("/api/analyses/titles"' in events_js


def run_all():
    tests = [
        test_frontend_defaults_to_same_origin_when_hosted,
        test_autocomplete_uses_configured_api_base_url,
    ]

    for test in tests:
        test()
        print(f"OK {test.__name__}")

    print("FRONTEND HOSTING CONTRACT TESTS PASSED")


if __name__ == "__main__":
    run_all()
