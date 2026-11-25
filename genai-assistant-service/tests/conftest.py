import pytest

from genai_assistant_service.services.assistant import AssistantService
from genai_assistant_service.standins.landscape import Landscape
from genai_assistant_service.tools.catalog import tools


@pytest.fixture
def landscape():
    return Landscape()


@pytest.fixture
def make_assistant(landscape, monkeypatch):
    monkeypatch.delenv("E2A_PROVIDER_PROFILE", raising=False)
    monkeypatch.delenv("E2A_WORKLOAD_IDENTITY", raising=False)

    def make(**kwargs):
        return AssistantService(tools=tools(transports=landscape.transports()), **kwargs)
    return make


@pytest.fixture
def assistant(make_assistant):
    return make_assistant()


def ask(assistant, text, user="ana@acme.example", role="investigator", key=None):
    return assistant.ask(text, "acme", user, role, key)


@pytest.fixture(autouse=True)
def isolated_firestore_collection(monkeypatch):
    """With GENAI_STATE_BACKEND=firestore (CI, on the emulator) each test gets its own collection."""
    import os
    import uuid
    if os.getenv("GENAI_STATE_BACKEND") == "firestore":
        monkeypatch.setenv("GENAI_FIRESTORE_COLLECTION", f"genai-{uuid.uuid4().hex[:10]}")
