from database import User, Broker


def test_user_password_hashing():
    """Test that passwords are hashed and can be verified."""
    user = User(username="testuser")
    user.set_password("securepassword")

    assert user.password_hash != "securepassword"
    assert user.check_password("securepassword") is True
    assert user.check_password("wrongpassword") is False


def test_broker_to_dict():
    """Test the to_dict method of the Broker model."""
    broker = Broker(
        name="Test Broker",
        ip="127.0.0.1",
        port=1883,
        username="user",
        password="pass",
        user_id=1,
    )

    data = broker.to_dict()
    assert data["name"] == "Test Broker"
    assert data["ip"] == "127.0.0.1"
    assert data["port"] == 1883
    assert data["username"] == "user"
    assert data["password"] == "pass"
