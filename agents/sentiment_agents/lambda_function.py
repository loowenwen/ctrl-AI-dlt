import json
import os
import asyncio
import logging
from sentiment_final import graph
from dataclasses import is_dataclass, asdict
import uuid, time, logging
BOOT_ID = str(uuid.uuid4())
logging.info("COLD START BOOT_ID=%s", BOOT_ID)


def _jsonable(obj):
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if is_dataclass(obj):
        return _jsonable(asdict(obj))
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(x) for x in obj]
    if hasattr(obj, "model_dump"):
        try:
            return _jsonable(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, "dict"):
        try:
            return _jsonable(obj.dict())
        except Exception:
            pass
    if hasattr(obj, "to_dict"):
        try:
            return _jsonable(obj.to_dict())
        except Exception:
            pass
    if hasattr(obj, "to_json"):
        try:
            j = obj.to_json()
            return json.loads(j) if isinstance(j, str) else _jsonable(j)
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return _jsonable(vars(obj))
        except Exception:
            pass
    return str(obj)

def _safe_text(val):
    """
    Coerce any object to a clean UTF-8 string for JSON responses.
    Prevents weird escape artifacts and unpaired surrogates.
    """
    if val is None:
        return ""
    if isinstance(val, bytes):
        try:
            val = val.decode("utf-8", "replace")
        except Exception:
            val = val.decode("latin-1", "replace")
    else:
        try:
            val = str(val)
        except Exception:
            val = repr(val)
    # Normalize newlines and strip trailing NULs/control chars
    val = val.replace("\r\n", "\n").replace("\r", "\n")
    # Ensure we don't carry stray surrogates
    val = val.encode("utf-8", "surrogatepass").decode("utf-8", "replace")
    return val

# --- Timeout controls (local + AWS) ---
DEFAULT_TOTAL_TIMEOUT = int(os.getenv("TOTAL_TIMEOUT_SECONDS", "55"))  # local default cap
SAFETY_BUFFER_MS = int(os.getenv("TIMEOUT_SAFETY_BUFFER_MS", "2000"))  # leave a buffer for marshalling/logs

log = logging.getLogger(__name__)
if not log.handlers:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

def _deadline_seconds(context):
    """
    Returns the number of seconds we can safely run before Lambda's hard timeout.
    Uses AWS context when available; otherwise falls back to DEFAULT_TOTAL_TIMEOUT.
    """
    try:
        ms = context.get_remaining_time_in_millis()  # available in real Lambda
        return max(1, int((ms - SAFETY_BUFFER_MS) / 1000))
    except Exception:
        return DEFAULT_TOTAL_TIMEOUT

def handler(event, context):
    """
    AWS Lambda handler for sentiment analysis workflow

    Accepts:
    - Raw string event
    - {"text": "..."} (direct invoke)
    - API Gateway proxy: {"body":"{...}"}
    - SQS/SNS formats (best-effort)
    """
    try:
        # 1) Extract text safely from a variety of payloads
        input_text = ""
        if isinstance(event, str):
            input_text = event
        elif isinstance(event, dict):
            # API Gateway proxy?
            if "body" in event and isinstance(event["body"], str) and event["body"]:
                try:
                    body_json = json.loads(event["body"])
                    input_text = body_json.get("text") or body_json.get("prompt") or ""
                except json.JSONDecodeError:
                    # body is just raw text
                    input_text = event["body"]

            # Direct invoke, or already-parsed JSON
            if not input_text:
                input_text = event.get("text") or event.get("prompt") or ""

            # SQS/SNS (best-effort)
            if not input_text and "Records" in event and isinstance(event["Records"], list):
                for rec in event["Records"]:
                    if "body" in rec:
                        try:
                            b = json.loads(rec["body"])
                            input_text = b.get("text") or b.get("prompt") or ""
                        except Exception:
                            input_text = rec.get("body") or ""
                    if input_text:
                        break

        input_text = (input_text or "").strip()
        if not input_text:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "No input text provided"})
            }

        # 2) Run graph with a hard wall-clock timeout
        async def _run_graph():
            # If graph is synchronous, run it in a thread to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: graph(input_text))

        timeout = _deadline_seconds(context)
        try:
            result = asyncio.run(asyncio.wait_for(_run_graph(), timeout=timeout))
        except asyncio.TimeoutError:
            log.error("Graph execution timed out after %ss", timeout)
            return {
                "statusCode": 504,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"graph timed out after {timeout}s", "input": input_text})
            }

        # 3) Extract final agent output (assuming final node id is 'sentiment')
        final_output = None
        try:
            final_output = getattr(result, "outputs", {}).get("sentiment")
        except Exception:
            pass

        # Fallbacks if structure differs
        if final_output is None:
            try:
                final_output = result.results["sentiment"].result
            except Exception:
                final_output = result

        # Safely coerce the final output to clean text
        final_output_text = _safe_text(final_output)

        # 4) Build JSON body
        response_body = {
            "input": input_text,
            "output": final_output_text,
            "output_lines": [ln for ln in final_output_text.split("\n") if ln.strip() != ""],
            "status": getattr(result, "status", None),
            "execution_order": [getattr(n, "node_id", str(n)) for n in getattr(result, "execution_order", [])],
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(_jsonable(response_body), ensure_ascii=False)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(e),
                "input": _jsonable(event)
            })
        }