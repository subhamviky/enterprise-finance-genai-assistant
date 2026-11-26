"""Probe what a Gemini API model accepts, with the exact features the E2A adapter sends (GCP-01/GCP-02).

    GEMINI_API_KEY=... python landscape/probe_model.py MODEL_ID [MODEL_ID ...]

For each model it makes four small calls and prints one line each:
  plain       a user message only
  system      the same, with a system instruction (the adapter puts the agent's prompt there)
  thinking    the system instruction and a thinking level of LOW (the adapter's reasoning effort)
  json        an agent-style request for a JSON answer, then checks the reply parses (a code fence is tolerated)
A line says ok or the error (first 160 characters), the seconds taken and the tokens used. About 4 calls per model; it
waits between calls (PROBE_PAUSE seconds, default 6) so a free-tier limit is not hit by the probe itself.
Nothing secret is printed: the key stays in the environment."""
import json
import os
import re
import sys
import time

from google import genai
from google.genai import types

SYSTEM = "You are IntentAgent. Classify the request. Answer as JSON {\"intent\": ..., \"order_id\": ...}."
USER = "Status of order ORD-7Q2K9X4M1B?"


def parses(text: str) -> bool:
    text = (text or "").strip()
    try:
        json.loads(text)
        return True
    except ValueError:
        match = re.search(r"\{.*\}", text, re.S)
        try:
            return bool(match and json.loads(match.group(0)))
        except ValueError:
            return False


def call(client, model, config):
    started = time.time()
    try:
        response = client.models.generate_content(model=model, contents=USER, config=config)
        used = getattr(response.usage_metadata, "total_token_count", None)
        return f"ok  {time.time() - started:5.1f}s tokens={used}", response.text
    except Exception as error:                                        # the point is to see the refusal
        return f"ERR {time.time() - started:5.1f}s {str(error)[:160]!r}", ""


def main(models) -> int:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("set GEMINI_API_KEY first")
        return 2
    client = genai.Client(api_key=key)
    pause = float(os.getenv("PROBE_PAUSE", "6"))
    for model in models:
        print(f"== {model}")
        variants = [
            ("plain", types.GenerateContentConfig()),
            ("system", types.GenerateContentConfig(system_instruction=SYSTEM)),
            ("thinking", types.GenerateContentConfig(system_instruction=SYSTEM,
                                                     thinking_config=types.ThinkingConfig(thinking_level="LOW"))),
            ("json", types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.0, max_output_tokens=512)),
        ]
        for name, config in variants:
            status, text = call(client, model, config)
            extra = f" parses_as_json={parses(text)}" if name == "json" and status.startswith("ok") else ""
            print(f"  {name:9s} {status}{extra}")
            time.sleep(pause)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
