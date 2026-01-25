# 📡 MQTT Antena

MQTT Antena is a simple, modern, web-based MQTT client application built with Python and Flask. It allows users to manage multiple MQTT broker connections by connecting to a broker, monitor real-time message streams, and publish messages through a clean web interface. It is intended to be used as a development tool for self-hosted MQTT-based applications.

##  Features

-   **User Accounts:** Simple registration (with password confirmation) and login system.
-   **Password Reset:** Command-line tool for resetting user passwords.
-   **Broker Management:** Add, edit, connect, and delete multiple MQTT broker connections.
-   **Live Subscription:** Real-time message monitoring using Server-Sent Events (SSE).
-   **Subscription Filtering:** Subscribe to specific topics or use wildcards (`#`).
-   **Message Publishing:** Send MQTT messages to any connected broker.
-   **Aesthetics:** Modern, responsive UI with light and dark mode support.
-   **Persistence:** Persistent database storage using Docker volumes.
-   **Developer Friendly:** Includes a `Makefile` for common tasks and development.

##  Tech Stack

-   **Backend:** Python 3.11, Flask, Flask-SQLAlchemy, Paho-MQTT, Gunicorn, Eventlet.
-   **Frontend:** HTML5, CSS3 (Vanilla), JavaScript (Minimal for SSE/Theme).
-   **Database:** SQLite.
-   **Deployment:** Docker, Docker Compose.
-   **Tooling:** Ruff (Linting/Formatting), Make.

##  Security

- **Password Hashing:** User passwords are encrypted using `pbkdf2:sha256` hashing.
- **Secret Key:** The application uses a `SECRET_KEY` for session security. **In production, you must set this via an environment variable.**

##  Configuration

You can configure the application using the following environment variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Flask secret key for sessions | `super_secret_key_dev_only` |
| `DATABASE_URL`| SQLAlchemy database URI | `sqlite:///../data/antena.db` |

##  Data Storage

### What is stored
- **User Accounts:** Usernames and securely hashed passwords.
- **Broker Configs:** Names, IP addresses, ports, and optional MQTT credentials for each registered broker.

### What is NOT stored
- **Connection Status:** Broker connectivity is runtime-only and starts as "Disconnected" on every app restart.
- **Message History:** MQTT messages are streamed in real-time and are not saved to the database. History is lost on page refresh or app restart.

##  Getting Started

### Quick Start (using Docker Hub)
If you just want to run the application without downloading the source code, use the following `docker-compose.yml`:

```yaml
version: '3.8'
services:
  mqtt-antena:
    image: fbossolan/mqtt-antena:latest
    container_name: mqtt-antena
    ports:
      - "8585:8585"
    volumes:
      - ./data:/app/data
    environment:
      - SECRET_KEY=your_secret_key_here
    restart: unless-stopped
```

Then run:
```bash
docker-compose up -d
```

### Developing from Source
#### Prerequisites

-   [Docker](https://www.docker.com/get-started)
-   [Docker Compose](https://docs.docker.com/compose/install/)
-   [pyenv](https://github.com/pyenv/pyenv) (Optional, but recommended)

#### Local Setup (Virtual Environment)

For local development, linting, and formatting, it is recommended to use the provided `venv` target:

1. **Ensure you have Python 3.11 installed** (e.g., via `pyenv install 3.11.14`).
2. **Create and sync the virtual environment**:
   ```bash
   make venv
   ```
3. **Activate the environment**:
   ```bash
   source .venv/bin/activate
   ```

#### Running the Application (Recommended)

The easiest way to run MQTT Antena is using Docker Compose:

```bash
docker-compose up -d --build
```

Access the application at: **http://localhost:8585**

### Development Workflow

A `Makefile` is provided to simplify development tasks:

-   **Virtual Env:** `make venv` (Creates and syncs the `.venv`).
-   **Build Image:** `make build` (Builds the Docker image).
-   **Run Application:** `make run` (Starts app via Docker Compose).
-   **Linting:** `make lint` (Runs Ruff check).
-   **Formatting:** `make format` (Runs Ruff format).
-   **Password Reset:** `make reset-password user=USER pass=PASS` (Resets a user password).
-   **Cleanup:** `make clean` (Removes caches and `.venv`).
-   **Publish Image:** `make publish TAG=vx.y.z` (Pushes to `flvbssln/mqtt-antena`).
-   **Destroy Project:** `make destroy` (Removes local containers, images, and volumes).

##  Project Structure

```text
mqtt-antena/
├── src/                # Python source code
│   ├── app.py          # Flask application and routes
│   ├── database.py     # SQLAlchemy models
│   ├── mqtt_manager.py # MQTT client logic
│   ├── static/         # CSS and static assets
│   └── templates/      # Jinja2 HTML templates
├── data/               # Persistent database storage (ignored by git)
├── Dockerfile          # Docker build configuration
├── docker-compose.yml  # Docker Compose orchestration
├── Makefile            # Automation recipes
├── requirements.txt    # Python dependencies
└── .gitignore          # Git ignore rules
```

##  License

This project is licensed under the MIT License.
