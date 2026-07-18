"""P7-08: Model/Node/Deployment ORM model tests.

Verifies:
- Endpoint is encrypted on storage.
- Credential is encrypted on storage.
- repr does not leak endpoint/credential.
- exposure_type enum works.
"""
from __future__ import annotations

from src.modules.memories.encryption import get_encryption_service
from src.modules.model_gateway.models import ModelDefinition, ModelProviderType, ModelType
from src.modules.nodes.models import (
    DeploymentStatus,
    ExposureType,
    ModelDeployment,
    ModelNode,
    NodeHealthStatus,
    NodeStatus,
)


class TestModelDefinition:
    def test_create_model_definition(self, test_db_session):
        model = ModelDefinition(
            name="test-model",
            version="1.0.0",
            provider=ModelProviderType.LOCAL.value,
            model_type=ModelType.CHAT.value,
            enabled=True,
        )
        test_db_session.add(model)
        test_db_session.flush()
        assert model.id is not None
        assert model.provider == "local"
        assert model.enabled is True

    def test_repr_no_sensitive_data(self, test_db_session):
        model = ModelDefinition(
            name="test",
            version="1.0",
            provider="local",
            model_type="chat",
        )
        r = repr(model)
        assert "name=test" in r
        # No credential fields exist on ModelDefinition.
        assert "password" not in r.lower()
        assert "api_key" not in r.lower()


class TestModelNode:
    def test_endpoint_encrypted_on_storage(self, test_db_session):
        enc = get_encryption_service()
        plaintext = "http://secret-node.example.edu:8080/v1"
        node = ModelNode(
            name="test-node",
            endpoint_encrypted=enc.encrypt(plaintext),
            exposure_type=ExposureType.INGRESS.value,
            health_status=NodeHealthStatus.ONLINE.value,
            status=NodeStatus.REGISTERING.value,
        )
        test_db_session.add(node)
        test_db_session.flush()

        # Stored value must be ciphertext, not plaintext.
        assert node.endpoint_encrypted != plaintext
        assert "secret-node" not in node.endpoint_encrypted
        # Decryption recovers the plaintext.
        assert enc.decrypt(node.endpoint_encrypted) == plaintext

    def test_credential_encrypted_on_storage(self, test_db_session):
        enc = get_encryption_service()
        secret_cred = "super-secret-api-key"
        node = ModelNode(
            name="test-node",
            endpoint_encrypted=enc.encrypt("http://node.example/v1"),
            credential_encrypted=enc.encrypt(secret_cred),
            exposure_type=ExposureType.NODEPORT.value,
        )
        test_db_session.add(node)
        test_db_session.flush()

        assert node.credential_encrypted != secret_cred
        assert "super-secret-api-key" not in node.credential_encrypted
        assert enc.decrypt(node.credential_encrypted) == secret_cred

    def test_repr_does_not_leak_endpoint_or_credential(self, test_db_session):
        enc = get_encryption_service()
        node = ModelNode(
            name="test-node",
            endpoint_encrypted=enc.encrypt("http://leak-me.example/v1"),
            credential_encrypted=enc.encrypt("leak-this-credential"),
            exposure_type=ExposureType.LOCAL.value,
        )
        r = repr(node)
        assert "leak-me" not in r
        assert "leak-this-credential" not in r
        assert "endpoint_encrypted" not in r
        assert "credential_encrypted" not in r

    def test_exposure_type_enum_values(self):
        assert ExposureType.INGRESS.value == "INGRESS"
        assert ExposureType.NODEPORT.value == "NODEPORT"
        assert ExposureType.LOCAL.value == "LOCAL"
        assert ExposureType.MOCK.value == "MOCK"

    def test_health_status_enum_values(self):
        assert NodeHealthStatus.ONLINE.value == "ONLINE"
        assert NodeHealthStatus.DEGRADED.value == "DEGRADED"
        assert NodeHealthStatus.OFFLINE.value == "OFFLINE"

    def test_mock_exposure_needs_no_real_endpoint(self, test_db_session):
        enc = get_encryption_service()
        node = ModelNode(
            name="mock-node",
            endpoint_encrypted=enc.encrypt("mock://localhost"),
            exposure_type=ExposureType.MOCK.value,
        )
        test_db_session.add(node)
        test_db_session.flush()
        assert node.exposure_type == "MOCK"


class TestModelDeployment:
    def test_create_deployment(self, test_db_session):
        enc = get_encryption_service()
        model = ModelDefinition(
            name="m", version="1", provider="local", model_type="chat"
        )
        node = ModelNode(
            name="n",
            endpoint_encrypted=enc.encrypt("http://x/v1"),
            exposure_type="LOCAL",
        )
        test_db_session.add_all([model, node])
        test_db_session.flush()

        dep = ModelDeployment(
            model_id=model.id,
            node_id=node.id,
            version="1.0.0",
            status=DeploymentStatus.DEPLOYED.value,
            priority=10,
        )
        test_db_session.add(dep)
        test_db_session.flush()
        assert dep.id is not None
        assert dep.priority == 10

    def test_deployment_repr_no_sensitive_data(self):
        r = repr(
            ModelDeployment(
                model_id=None,  # type: ignore[arg-type]
                node_id=None,  # type: ignore[arg-type]
            )
        )
        assert "endpoint" not in r.lower()
        assert "credential" not in r.lower()
