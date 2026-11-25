"""genai-assistant-service - FastAPI entry point (scaffolded by P0)."""
import logging

from fastapi import FastAPI

logger = logging.getLogger("genai_assistant_service")

app = FastAPI(title="genai-assistant-service")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by the container HEALTHCHECK and the platform."""
    return {"status": "UP", "service": "genai-assistant-service"}
