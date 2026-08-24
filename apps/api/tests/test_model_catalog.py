import pytest

from agentq_api.services import model_catalog_service as svc


@pytest.fixture(autouse=True)
def _reset_catalog_cache():
    svc._cache["entries"] = None
    svc._cache["fetched_at"] = 0.0
    yield
    svc._cache["entries"] = None
    svc._cache["fetched_at"] = 0.0


async def _fake_get_catalog():
    return svc._FALLBACK_CATALOG


async def test_get_catalog_falls_back_when_network_unavailable(monkeypatch):
    class _FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            raise RuntimeError("no network")

    monkeypatch.setattr(svc.httpx, "AsyncClient", lambda timeout=5.0: _FailingClient())

    entries = await svc.get_catalog()

    assert entries == svc._FALLBACK_CATALOG
    assert any(e.vendor == "openai" for e in entries)


async def test_catalog_endpoint_free_only_returns_top_free_models(client, monkeypatch):
    monkeypatch.setattr("agentq_api.routers.model_configs.get_catalog", _fake_get_catalog)

    response = await client.get("/api/v1/models/catalog", params={"free_only": "true", "limit": 5})

    assert response.status_code == 200
    data = response.json()
    assert 0 < len(data) <= 5
    assert all(m["is_free"] for m in data)


async def test_catalog_endpoint_search_scopes_by_provider(client, monkeypatch):
    monkeypatch.setattr("agentq_api.routers.model_configs.get_catalog", _fake_get_catalog)

    response = await client.get("/api/v1/models/catalog", params={"provider": "openai", "q": "4o"})

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(m["vendor"] == "openai" for m in data)
    assert all("4o" in m["id"].lower() for m in data)


async def test_catalog_endpoint_gemini_provider_maps_to_google_vendor(client, monkeypatch):
    monkeypatch.setattr("agentq_api.routers.model_configs.get_catalog", _fake_get_catalog)

    response = await client.get("/api/v1/models/catalog", params={"provider": "gemini"})

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(m["vendor"] == "google" for m in data)
