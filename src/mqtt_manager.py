import paho.mqtt.client as mqtt
from datetime import datetime
import threading
import queue
import time

# Global registry of connected clients
# { broker_id: ActiveClient }
connected_clients = {}

# Global message buffer for SSE
# In a robust app, use Redis or per-session queues.
# Here we use a simple list that gets trimmed, or a queue that broadcasters read from.
# To keep it simple for SSE: we'll have a listener mechanism.
# listeners = [queue.Queue(), ...]
listeners = []
listeners_lock = threading.Lock()


def broadcast_message(message_data):
    """Push message to all active SSE listeners"""
    with listeners_lock:
        # iterate copy to avoid modification issues if we were to remove closed queues here
        # but typically queues just fill up if not consumed.
        # For this simple app, we just push.
        for q in listeners:
            try:
                q.put_nowait(message_data)
            except queue.Full:
                pass


class ActiveClient:
    def __init__(self, broker_id, name, ip, port, user=None, password=None):
        self.broker_id = broker_id
        self.name = name
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        self.client = mqtt.Client(client_id=f"antena_{broker_id}_{int(time.time())}")
        self.is_connected = False
        self.connection_error = None
        self.subscribed_topics = set()

        # User snippet logic adaptation
        if self.user and self.password:
            self.client.username_pw_set(self.user, self.password)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def connect(self):
        try:
            self.client.connect(self.ip, self.port, 60)
            self.client.loop_start()  # Non-blocking
            return True, None
        except Exception as e:
            self.connection_error = str(e)
            return False, str(e)

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.is_connected = False

    def update_subscription(self, topic):
        # Unsubscribe from everything else to ensure clean state
        # (simpler than tracking specific sets for this use case)
        if self.subscribed_topics:
            for t in list(self.subscribed_topics):
                self.client.unsubscribe(t)
                self.subscribed_topics.remove(t)

        target = topic if topic else "#"
        print(f"Subscribing to {target} on {self.name}", flush=True)
        self.client.subscribe(target)
        self.subscribed_topics.add(target)

    def clear_subscription(self):
        if self.subscribed_topics:
            for t in list(self.subscribed_topics):
                self.client.unsubscribe(t)
            self.subscribed_topics.clear()
            print(f"Cleared subscriptions on {self.name}", flush=True)

    def publish(self, topic, payload):
        self.client.publish(topic, payload)

    # Callbacks
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            self.connection_error = None
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] {self.name}: Connected!",
                flush=True,
            )
            # Note: We do NOT auto-subscribe to '#' here unless the user requested it.
            # But per user snippet: "Connected! Subscribing to messages..." -> client.subscribe("#")
            # The prompt says: "The user must be able to select ... and subscribe to a topic... If no topic is provided, then all..."
            # So we wait for the Subscribe action from UI.
        else:
            self.is_connected = False
            self.connection_error = f"Connection failed code {rc}"
            print(self.connection_error, flush=True)

    def on_message(self, client, userdata, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            payload_str = msg.payload.decode()
        except:
            payload_str = str(msg.payload)

        data = {
            "broker_id": self.broker_id,
            "broker_name": self.name,
            "timestamp": timestamp,
            "topic": msg.topic,
            "payload": payload_str,
        }
        # Send to global UI stream
        broadcast_message(data)
        print(f"[{timestamp}] {self.name} | {msg.topic}: {payload_str}", flush=True)

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        print(f"{self.name} disconnected. RC: {rc}", flush=True)


# Manager functions
def get_client(broker_id):
    return connected_clients.get(int(broker_id))


def add_client(broker_obj):
    # If already exists, disconnect first (refresh)
    if broker_obj.id in connected_clients:
        remove_client(broker_obj.id)

    client = ActiveClient(
        broker_obj.id,
        broker_obj.name,
        broker_obj.ip,
        broker_obj.port,
        broker_obj.username,
        broker_obj.password,
    )
    connected_clients[broker_obj.id] = client
    return client


def remove_client(broker_id):
    if broker_id in connected_clients:
        try:
            connected_clients[broker_id].disconnect()
        except:
            pass
        del connected_clients[broker_id]
