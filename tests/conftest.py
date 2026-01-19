import pytest
import os
import sys
import subprocess
import time
import socket

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from app import app as flask_app
from database import db


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    flask_app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture(scope="session")
def mqtt_broker():
    """Spawn a temporary Mosquitto broker using Docker."""
    container_name = f"mqtt_test_broker_{int(time.time())}"
    # Mosquitto 2.0+ needs a config to allow anonymous connections outside localhost
    # We can use a simple one-liner for the config
    docker_cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        "18883:1883",
        "eclipse-mosquitto:2.0",
        "sh",
        "-c",
        "printf 'listener 1883\\nallow_anonymous true\\n' > /tmp/mosquitto.conf && mosquitto -c /tmp/mosquitto.conf",
    ]

    try:
        subprocess.run(docker_cmd, check=True)
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Docker not available or port 1883 in use: {e}")

    # Wait for broker to be ready
    host = "127.0.0.1"
    port = 18883
    max_retries = 20
    time.sleep(2)  # Give docker a moment to actually start the process
    for i in range(max_retries):
        try:
            with socket.create_connection((host, port), timeout=1):
                break
        except (socket.error, ConnectionRefusedError):
            time.sleep(1)
    else:
        subprocess.run(["docker", "rm", "-f", container_name])
        pytest.fail("Mosquitto broker failed to start in time")

    yield {"host": host, "port": port}

    # Teardown
    subprocess.run(["docker", "rm", "-f", container_name])
