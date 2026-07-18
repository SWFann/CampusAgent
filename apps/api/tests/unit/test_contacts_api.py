"""Contact API regression tests."""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import auth_headers, register_and_login, set_auth_cookies


def test_contact_request_accept_and_delete(db_client: TestClient) -> None:
    alice = register_and_login(
        db_client, email="contacts_alice@example.edu", student_no="20267001"
    )
    bob = register_and_login(
        db_client, email="contacts_bob@example.edu", student_no="20267002"
    )

    set_auth_cookies(db_client, alice)
    create_resp = db_client.post(
        "/api/v1/contacts/requests",
        json={"target_user_id": bob["user_id"]},
        headers=auth_headers(alice["csrf_token"]),
    )
    assert create_resp.status_code == 201
    request_id = create_resp.json()["data"]["id"]

    outgoing_resp = db_client.get("/api/v1/contacts/requests")
    assert outgoing_resp.status_code == 200
    assert len(outgoing_resp.json()["data"]["outgoing"]) == 1

    set_auth_cookies(db_client, bob)
    incoming_resp = db_client.get("/api/v1/contacts/requests")
    assert incoming_resp.status_code == 200
    assert len(incoming_resp.json()["data"]["incoming"]) == 1

    accept_resp = db_client.post(
        f"/api/v1/contacts/requests/{request_id}/accept",
        headers=auth_headers(bob["csrf_token"]),
    )
    assert accept_resp.status_code == 200

    contacts_resp = db_client.get("/api/v1/contacts")
    assert contacts_resp.status_code == 200
    contacts = contacts_resp.json()["data"]["contacts"]
    assert contacts[0]["user"]["id"] == alice["user_id"]

    delete_resp = db_client.delete(
        f"/api/v1/contacts/{alice['user_id']}",
        headers=auth_headers(bob["csrf_token"]),
    )
    assert delete_resp.status_code == 204

    empty_resp = db_client.get("/api/v1/contacts")
    assert empty_resp.status_code == 200
    assert empty_resp.json()["data"]["total"] == 0


def test_cannot_add_self_as_contact(db_client: TestClient) -> None:
    alice = register_and_login(
        db_client, email="contacts_self@example.edu", student_no="20267003"
    )
    set_auth_cookies(db_client, alice)

    resp = db_client.post(
        "/api/v1/contacts/requests",
        json={"target_user_id": alice["user_id"]},
        headers=auth_headers(alice["csrf_token"]),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "CONTACT_SELF_NOT_ALLOWED"
