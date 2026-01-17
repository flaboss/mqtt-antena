import eventlet

eventlet.monkey_patch()

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    Response,
    stream_with_context,
)
from database import db, User, Broker
from mqtt_manager import (
    add_client,
    get_client,
    remove_client,
    listeners,
    listeners_lock,
)
import json

import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key_dev_only")

# Create data directory for persistence
# We are in src/, so data is in ../data (root)
data_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
os.makedirs(data_dir, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(data_dir, 'antena.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


with app.app_context():
    db.create_all()


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("brokers"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "error")
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            session["user_id"] = new_user.id
            flash("Account created! Logged in.", "success")
            return redirect(url_for("brokers"))
    return render_template("register.html")


@app.route("/howto")
def howto():
    return render_template("howto.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            flash("Logged in!", "success")
            return redirect(url_for("brokers"))
        else:
            flash("Invalid credentials", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))


# --- Broker Management ---


@app.route("/brokers/edit/<int:broker_id>", methods=["GET", "POST"])
@login_required
def edit_broker(broker_id):
    broker = Broker.query.get_or_404(broker_id)
    if request.method == "POST":
        broker.name = request.form.get("name")
        broker.ip = request.form.get("ip")
        broker.port = int(request.form.get("port", 1883))
        broker.username = request.form.get("username")
        broker.password = request.form.get("password")

        if not broker.name:
            broker.name = broker.ip

        # If connected, reconnect to apply changes?
        # Simpler: just save. User can reconnect manually.
        # Or auto-disconnect. Let's auto-disconnect to avoid stale state.
        remove_client(broker.id)

        db.session.commit()
        flash("Broker updated", "success")
        return redirect(url_for("brokers"))

    return render_template("edit_broker.html", broker=broker)


@app.route("/brokers", methods=["GET", "POST"])
@login_required
def brokers():
    if request.method == "POST":
        if "add" in request.form:
            name = request.form.get("name")
            ip = request.form.get("ip")
            port = int(request.form.get("port", 1883))
            user = request.form.get("username")
            password = request.form.get("password")

            if not name:
                name = ip

            new_broker = Broker(
                name=name, ip=ip, port=port, username=user, password=password
            )
            db.session.add(new_broker)
            db.session.commit()
            flash("Broker added", "success")

        elif "delete" in request.form:
            b_id = request.form.get("broker_id")
            broker = Broker.query.get(b_id)
            if broker:
                # Disconnect if connected
                remove_client(broker.id)
                db.session.delete(broker)
                db.session.commit()
                flash("Broker deleted", "success")

        elif "connect" in request.form:
            b_id = request.form.get("broker_id")
            broker = Broker.query.get(b_id)
            if broker:
                client = add_client(broker)
                success, error = client.connect()
                if success:
                    flash(f"Connected to {broker.name}", "success")
                else:
                    flash(f"Error connecting: {error}", "error")

        elif "disconnect" in request.form:
            b_id = request.form.get("broker_id")
            remove_client(int(b_id))
            flash("Disconnected", "info")

        return redirect(url_for("brokers"))

    # GET
    all_brokers = Broker.query.all()
    # Augment with status
    brokers_data = []
    for b in all_brokers:
        client = get_client(b.id)
        status = "disconnected"
        if client:
            if client.is_connected:
                status = "connected"
            elif client.connection_error:
                status = "error"

        brokers_data.append(
            {
                "obj": b,
                "status": status,
                "error": client.connection_error if client else None,
            }
        )

    return render_template("brokers.html", brokers=brokers_data)


# --- Subscription ---


@app.route("/subscription")
@login_required
def subscription():
    # Only active clients
    # We also want to know if they are listening to something to show correct button state
    active_brokers_data = []

    # We might have a selected broker in the query or defaulting to first
    # But the UI allows selecting from dropdown.
    # To make the button toggle correctly, the UI needs to know the state of the *selected* broker.
    # Since the dropdown changes via JS (or requires reload),
    # for simplicity in this "no-JS" preference app, we can just pass the list
    # and let the backend actions redirect back.
    # However, to show "Stop" vs "Start", checking the first active one or passing all states is best.

    for b in Broker.query.all():
        c = get_client(b.id)
        if c and c.is_connected:
            # Check if has any subscription
            is_listening = len(c.subscribed_topics) > 0
            current_topic = list(c.subscribed_topics)[0] if is_listening else ""

            active_brokers_data.append(
                {
                    "id": c.broker_id,
                    "name": c.name,
                    "is_listening": is_listening,
                    "current_topic": current_topic,
                }
            )

    return render_template("subscription.html", active_brokers=active_brokers_data)


@app.route("/toggle_listen", methods=["POST"])
@login_required
def toggle_listen():
    broker_id = request.form.get("broker_id")
    topic = request.form.get("topic")
    action = request.form.get("action")  # 'start' or 'stop'

    if not broker_id:
        flash("Select a broker", "error")
        return redirect(url_for("subscription"))

    client = get_client(int(broker_id))
    if client:
        if action == "stop":
            client.clear_subscription()
            flash(f"Stopped listening on {client.name}", "info")
        else:
            client.update_subscription(topic)
            flash(
                f"Listening to {topic if topic else 'all topics'} on {client.name}",
                "success",
            )

    return redirect(url_for("subscription"))


# Remove old separate routes
# @app.route('/start_listen', methods=['POST']) ...
# @app.route('/stop_listen', methods=['POST']) ...


@app.route("/stream")
@login_required
def stream():
    def event_stream():
        import queue

        q = queue.Queue()
        with listeners_lock:
            listeners.append(q)
        try:
            while True:
                # 30s timeout to send keepalive
                try:
                    msg = q.get(timeout=20)
                    yield f"data: {json.dumps(msg)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            with listeners_lock:
                listeners.remove(q)

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


# --- Publish ---


@app.route("/publish", methods=["GET", "POST"])
@login_required
def publish():
    if request.method == "POST":
        broker_id = request.form.get("broker_id")
        topic = request.form.get("topic")
        message = request.form.get("message")

        client = get_client(int(broker_id))
        if client and client.is_connected:
            client.publish(topic, message)
            flash("Message published", "success")
        else:
            flash("Broker not connected", "error")

    active_brokers = [
        {"id": c.broker_id, "name": c.name}
        for c in [get_client(b.id) for b in Broker.query.all()]
        if c and c.is_connected
    ]
    return render_template("publish.html", active_brokers=active_brokers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8585, debug=True)
