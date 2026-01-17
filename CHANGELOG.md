# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-01-15

### Added
- **User Authentication**: Registration and login system with secure password hashing.
- **Broker Management**: Interface to add, edit, delete, and manage multiple MQTT broker connections.
- **Live Subscription**: Real-time message streaming using Server-Sent Events (SSE).
- **Flexible Subscriptions**: Support for specific topics and wildcards (`#`).
- **MQTT Publishing**: Ability to send messages to any connected broker.
- **Modern UI**: Clean design with Light and Dark mode support.
- **Persistence**: SQLite database with Docker volume mounting.
- **Project Tooling**: Comprehensive `Makefile` and `docker-compose.yml` for easy deployment and development.
- **Documentation**: Initial README, How-to guide, and project structure documentation.
