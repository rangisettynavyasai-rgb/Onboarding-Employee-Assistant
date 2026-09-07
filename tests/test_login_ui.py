from app.config import settings


def test_login_page_requires_google_client_id(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
    response = client.get("/")
    assert response.status_code == 503


def test_login_page_renders_google_client_id(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "12345.apps.googleusercontent.com")
    response = client.get("/")
    assert response.status_code == 200
    assert "accounts.google.com/gsi/client" in response.text
    assert "12345.apps.googleusercontent.com" in response.text
