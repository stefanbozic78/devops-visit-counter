from app import app


def test_home():
    client = app.test_client()
    response = client.get("/")
    data = response.get_json()
    assert response.status_code == 200
    assert data["message"] == "Hello DevOps"
    assert "host" in data  
    assert isinstance(data["host"], str)
    assert len(data["host"]) > 0