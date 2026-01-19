import time
import queue
from database import db, Broker
from mqtt_manager import add_client, remove_client, listeners, listeners_lock


def test_mqtt_flow(app, mqtt_broker):
    """Verify full MQTT cycle: connect, subscribe, publish, and receive."""
    with app.app_context():
        # 1. Setup a test broker in DB
        broker_obj = Broker(
            name="Integration Test Broker",
            ip=mqtt_broker["host"],
            port=mqtt_broker["port"],
            user_id=1,  # Mock user
        )
        db.session.add(broker_obj)
        db.session.commit()

        # 2. Connect
        client = add_client(broker_obj)
        connected, error = client.connect()
        assert connected is True, f"Failed to connect: {error}"

        # Wait for on_connect to set is_connected to True
        for _ in range(50):  # 5 seconds
            if client.is_connected:
                break
            time.sleep(0.1)
        assert client.is_connected is True, (
            f"Client connected but is_connected flag not set. Error: {client.connection_error}"
        )

        try:
            # 3. Subscribe
            topic = "test/integration"
            client.update_subscription(topic)
            time.sleep(1)  # Wait for subscription to be processed

            # 4. Setup SSE listener queue
            test_queue = queue.Queue()
            user_id = 1
            with listeners_lock:
                if user_id not in listeners:
                    listeners[user_id] = []
                listeners[user_id].append(test_queue)

            try:
                # 5. Publish
                message = "Hello MQTT"
                client.publish(topic, message)

                # 6. Wait for message in queue
                # Increased timeout to allow for network/docker latency
                received = test_queue.get(timeout=5)

                assert received["topic"] == topic
                assert received["payload"] == message
                assert "timestamp" in received

            finally:
                with listeners_lock:
                    if user_id in listeners:
                        listeners[user_id].remove(test_queue)

        finally:
            remove_client(broker_obj.id)


def test_mqtt_connection_failure(app):
    """Verify behavior when broker is unreachable."""
    with app.app_context():
        broker_obj = Broker(
            name="Unreachable Broker",
            ip="192.0.2.1",  # Non-routable IP
            port=1883,
            user_id=1,
        )

        client = add_client(broker_obj)
        connected, error = client.connect()
        assert connected is False
        # Case-insensitive check
        error_lower = error.lower()
        assert (
            "timed out" in error_lower
            or "refused" in error_lower
            or "error" in error_lower
        )
        remove_client(broker_obj.id)
