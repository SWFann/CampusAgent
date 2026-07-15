"""
Unit test for application factory
"""

from __future__ import annotations

from src.main import create_app


def test_app_factory_creates_multiple_isolated_instances():
    """Test that create_app() creates isolated instances"""
    app1 = create_app()
    app2 = create_app()

    # Verify instances are different objects
    assert id(app1) != id(app2)

    # Verify instance states are independent
    app1.state.test_value = "instance1"
    app2.state.test_value = "instance2"

    assert app1.state.test_value == "instance1"
    assert app2.state.test_value == "instance2"


def test_app_has_required_routes():
    """Test that app has required health check routes"""
    app = create_app()

    # Check health routes exist
    routes = [route.path for route in app.routes]

    assert "/health/live" in routes
    assert "/health/ready" in routes


def test_app_title_and_version():
    """Test that app has correct title and version"""
    app = create_app()

    assert app.title == "CampusAgent API"
    assert app.version == "0.1.0"
