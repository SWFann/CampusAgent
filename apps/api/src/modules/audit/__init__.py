"""Audit module boundary.

Public entrypoints: api, schemas, service, permissions, events, exceptions.
Other modules must append audit facts through the service layer, not Audit ORM models.
"""
