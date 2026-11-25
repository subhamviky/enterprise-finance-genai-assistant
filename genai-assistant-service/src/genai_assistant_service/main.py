"""genai-assistant-service - FastAPI entry point (scaffolded by P0, completed by hand)."""
import logging

from fastapi import FastAPI

from .routers.api import router
from .services.assistant import AssistantService

logger = logging.getLogger("genai_assistant_service")


def build_app(assistant: AssistantService) -> FastAPI:
    app = FastAPI(title="genai-assistant-service")
    app.state.assistant = assistant
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe used by the container HEALTHCHECK and the platform."""
        return {"status": "UP", "service": "genai-assistant-service"}

    return app


app = build_app(AssistantService())
