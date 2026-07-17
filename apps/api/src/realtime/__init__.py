"""
Realtime module for CampusAgent.

Provides WebSocket connection management, event envelope construction,
and pubsub backend for real-time message delivery.

Design principles:
- WebSocket auth via access_token Cookie (no URL tokens).
- Origin whitelist enforcement.
- Per-conversation subscription authorization.
- Event envelope aligned with WEBSOCKET_CONTRACT.md v1.0.
- Redis Pub/Sub backend with in-memory fallback for tests.
- No sensitive data in logs or events.
"""
