"""Notifications module boundary.

Public entrypoints: api, schemas, service, permissions, events, exceptions.
Other modules must emit notification requests through services or events, not Notifications ORM models.
"""
