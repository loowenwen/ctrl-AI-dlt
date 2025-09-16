import requests
import json
from typing import Any, Dict

URL = "http://localhost:9000/2015-03-31/functions/function/invocations"

def _pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)

def test_local_lambda(text: str):
    """Test the sentiment analysis lambda running in local Docker container"""

    payload: Dict[str, Any] = {"text": text}

    resp = requests.post(URL, json=payload, headers={"Content-Type": "application/json"})
    print("Status Code:", resp.status_code)

    # First try to parse the outer body as JSON
    try:
        outer = resp.json()
        # API Gateway proxy shape? -> {'statusCode': ..., 'body': '...'}
        if isinstance(outer, dict) and "statusCode" in outer and "body" in outer:
            body = outer.get("body", "")
            # body might already be a dict or a JSON string
            if isinstance(body, (dict, list)):
                print("Response (proxy -> json):")
                print(_pretty(body))
            else:
                # Try parse as JSON string
                try:
                    inner = json.loads(body) if isinstance(body, str) else body
                    print("Response (proxy -> parsed):")
                    print(_pretty(inner))
                except Exception:
                    print("Response (proxy -> raw string):")
                    print(body if body is not None else "<empty>")
        else:
            # Plain JSON returned by handler (not proxy)
            print("Response (json):")
            print(_pretty(outer))
    except Exception:
        # Not JSON at all — show raw body for debugging
        raw = resp.text if resp.text is not None else ""
        print("Response (raw):")
        print(raw if raw.strip() != "" else "<empty body>")

if __name__ == "__main__":
    test_text = "Tell me about the Toa Payoh BTO launch sentiment"
    test_local_lambda(test_text)



