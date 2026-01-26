from database import db, User, Broker


def test_index_redirect(client):
    """Test that the index redirects to login when not logged in."""
    rv = client.get("/", follow_redirects=True)
    assert b"Login" in rv.data


def test_register_login_logout(client):
    """Test the full auth cycle: register -> login -> logout."""
    # Register
    rv = client.post(
        "/register",
        data={
            "username": "newuser",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=True,
    )
    assert b"Account created!" in rv.data

    # Check session
    with client.session_transaction() as sess:
        assert sess["user_id"] is not None

    # Logout
    rv = client.get("/logout", follow_redirects=True)
    assert b"Login" in rv.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_register_password_mismatch(client):
    """Test that registration fails when passwords don't match."""
    rv = client.post(
        "/register",
        data={
            "username": "mismatchuser",
            "password": "password123",
            "confirm_password": "differentpassword",
        },
        follow_redirects=True,
    )
    assert b"Passwords do not match" in rv.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_brokers_page_requires_login(client):
    """Verify that protected pages redirect to login."""
    rv = client.get("/brokers", follow_redirects=True)
    assert b"Login" in rv.data


def test_add_broker(client, mocker):
    """Test adding a broker (with MQTT mocked)."""
    # Create user and log in
    user = User(username="testuser")
    user.set_password("password")
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id

    # Add broker
    rv = client.post(
        "/brokers",
        data={
            "add": "true",
            "name": "My Broker",
            "ip": "127.0.0.1",
            "port": "1883",
            "username": "",
            "password": "",
        },
        follow_redirects=True,
    )

    assert b"Broker added" in rv.data
    broker = Broker.query.filter_by(name="My Broker").first()
    assert broker is not None
    assert broker.user_id == user.id


def test_subscription_isolation(client):
    """Verify that user A cannot see user B's brokers."""
    # Create user A and their broker
    user_a = User(username="user_a")
    user_a.set_password("pass")
    db.session.add(user_a)
    db.session.commit()

    broker_a = Broker(name="Broker A", ip="1.1.1.1", user_id=user_a.id)
    db.session.add(broker_a)
    db.session.commit()

    # Create user B and log in
    user_b = User(username="user_b")
    user_b.set_password("pass")
    db.session.add(user_b)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user_b.id

    # Check brokers page
    rv = client.get("/brokers")
    assert b"Broker A" not in rv.data


def test_publish_with_qos_and_retain(client, mocker):
    """Test publishing a message with QoS and Retain flags."""
    # Create user and log in
    user = User(username="pubuser")
    user.set_password("password")
    db.session.add(user)
    db.session.commit()

    broker = Broker(name="Pub Broker", ip="127.0.0.1", user_id=user.id)
    db.session.add(broker)
    db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id

    # Mock mqtt_manager functions
    mock_client = mocker.Mock()
    mock_client.is_connected = True
    mocker.patch("app.get_client", return_value=mock_client)

    # Publish with QoS 1 and Retain on
    rv = client.post(
        "/publish",
        data={
            "broker_id": str(broker.id),
            "topic": "test/topic",
            "message": "hello world",
            "qos": "1",
            "retain": "on",
        },
        follow_redirects=True,
    )

    assert b"Message published (QoS: 1, Retain: True)" in rv.data
    mock_client.publish.assert_called_once_with(
        "test/topic", "hello world", qos=1, retain=True
    )
