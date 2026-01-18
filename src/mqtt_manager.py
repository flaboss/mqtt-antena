import paho.mqtt.client as mqtt
from datetime import datetime
import threading
import queue
import time

connected_clients = {}

listeners = []
listeners_lock = threading.Lock()


def broadcast_message(message_data):
    """Push message to all active SSE listeners"""
    with listeners_lock:
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

        if self.user and self.password:
            self.client.username_pw_set(self.user, self.password)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def connect(self):
        try:
            self.client.connect(self.ip, self.port, 60)
            self.client.loop_start()
            return True, None
        except Exception as e:
            self.connection_error = str(e)
            return False, str(e)

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.is_connected = False

    def update_subscription(self, topic):
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

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            self.connection_error = None
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] {self.name}: Connected!",
                flush=True,
            )
        else:
            self.is_connected = False
            self.connection_error = f"Connection failed code {rc}"
            print(self.connection_error, flush=True)

    def on_message(self, client, userdata, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            payload_str = msg.payload.decode()
        except Exception:
            payload_str = str(msg.payload)

        data = {
            "broker_id": self.broker_id,
            "broker_name": self.name,
            "timestamp": timestamp,
            "topic": msg.topic,
            "payload": payload_str,
        }

        broadcast_message(data)
        print(f"[{timestamp}] {self.name} | {msg.topic}: {payload_str}", flush=True)

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        print(f"{self.name} disconnected. RC: {rc}", flush=True)


def get_client(broker_id):
    return connected_clients.get(int(broker_id))


def add_client(broker_obj):
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
        except Exception:
            pass
        del connected_clients[broker_id]
