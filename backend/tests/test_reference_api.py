from app.services.currency import SUPPORTED_CURRENCIES


def test_get_supported_currencies_matches_service_allowlist(client):
    response = client.get("/reference/currencies")

    assert response.status_code == 200
    assert set(response.json()) == SUPPORTED_CURRENCIES
    assert response.json() == sorted(response.json())  # sorted for a stable dropdown order


def test_get_supported_currencies_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/reference/currencies")

    assert response.status_code == 401