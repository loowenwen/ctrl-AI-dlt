from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
import os
try:
    import boto3
except Exception:
    boto3 = None

QB_DEBUG = os.environ.get("QB_DEBUG", "0") in ("1", "true", "True")

# --- Nova only (no Claude) ---
NOVA_PRO_MODEL_ID = os.environ.get("QB_NOVA_MODEL", "amazon.nova-pro-v1:0")

def _boto3_client(service: str, region: Optional[str] = None, profile: Optional[str] = None):
    if boto3 is None:
        raise RuntimeError("boto3 not available")
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region or os.environ.get("AWS_REGION", "us-east-1"))
        return session.client(service)
    return boto3.client(service, region_name=region or os.environ.get("AWS_REGION", "us-east-1"))

DEFAULT_ALLOW = [
    "tiktok.com", "youtube.com", "youtu.be",
    "hdb.gov.sg", "straitstimes.com", "channelnewsasia.com",
    "asiaone.com", "mothership.sg", "todayonline.com", "yahoo.com", "reddit.com"
]

DEFAULT_BLOCK = [
    
]

# ---- Bedrock model mapping (Nova only) ----
MODEL_MAP = {
    "nova": NOVA_PRO_MODEL_ID,
}

def _resolve_model_id(llm: Optional[str], override: Optional[str]) -> Optional[str]:
    if override:
        return override
    if not llm:
        return MODEL_MAP["nova"]
    # Any value supplied gets coerced to nova
    return MODEL_MAP["nova"]

def _invoke_bedrock_messages(body: Dict[str, Any], *, region: Optional[str] = None,
                             profile: Optional[str] = None) -> Dict[str, Any]:
    client = _boto3_client("bedrock-runtime", region, profile)
    resp = client.invoke_model(modelId=NOVA_PRO_MODEL_ID, body=json.dumps(body))
    return json.loads(resp["body"].read())

def _as_kw(v: Optional[str]) -> Optional[str]:
    return v.strip() if isinstance(v, str) and v.strip() else None

def _join_nonempty(parts: List[str], sep: str = " ") -> str:
    return sep.join([p for p in parts if p])

def rewrite_topic_with_llm(topic: str, *, llm: str = "nova", model_id: Optional[str] = None, region: Optional[str] = None, system_prompt: Optional[str] = None) -> str:
    """
    Send the draft topic to Amazon Nova (Bedrock) to craft a sharper
    search topic. Always uses Nova; Claude is not invoked here.
    """
    if not boto3:
        return topic
    region = region or os.environ.get("AWS_REGION", "us-east-1")
    if QB_DEBUG:
        print(f"[QB] Bedrock(Nova) call → model={NOVA_PRO_MODEL_ID} region={region}")

    sys_msg = system_prompt or (
        "You optimize search queries. Return one compact natural-language query that a person would type into Google,\n"
        "including key entities and hints for TikTok and YouTube when relevant. No explanations."
    )
    user_msg = (
        "Draft search context (may include metadata lines):\n\n"
        f"{topic}\n\n"
        "Return exactly one query line."
    )

    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": sys_msg}],
        "messages": [
            {"role": "user", "content": [{"text": user_msg}]}
        ],
        "inferenceConfig": {"maxTokens": 200, "temperature": 0.2, "topP": 0.9},
    }

    try:
        data = _invoke_bedrock_messages(body, region=region)
        out = (
            data.get("output", {})
            .get("message", {})
            .get("content", [{}])[0]
            .get("text", "")
            .strip()
        )
        if QB_DEBUG:
            print("[QB] Nova output:", out)
        return out or topic
    except Exception as e:
        if QB_DEBUG:
            print(f"[QB] Nova invoke failed: {e}")
        return topic

def build_topic_from_params(
    *,
    age: Optional[int] = None,
    town: Optional[str] = None,         # e.g., "Toa Payoh"
    flat_type: Optional[str] = None,    # e.g., "3-room", "4-room", "plus", "prime"
    launch_month: Optional[str] = None, # e.g., "July 2025"
    budget_sgd: Optional[int] = None,
    concerns: Optional[List[str]] = None,  # ["noise", "schools", "MRT", "amenities", ...]
    perspective: Optional[str] = None,     # "first-time buyer", "upgrader", etc.
    sentiment_prompt_hint: Optional[str] = None,
) -> str:
    """
    Convert form params into a single rich topic string for your websearch agent.
    """
    town_kw     = _as_kw(town)
    flat_kw     = _as_kw(flat_type)
    month_kw    = _as_kw(launch_month)
    perspective = _as_kw(perspective)
    concerns_kw = ", ".join(c for c in (concerns or []) if c)

    line1 = _join_nonempty([
        "HDB BTO", town_kw, month_kw, "(launch)"
    ])
    line2 = _join_nonempty([
        f"flat: {flat_kw}" if flat_kw else "",
        f"budget~{budget_sgd} SGD" if budget_sgd else "",
        f"age~{age}" if age else "",
        perspective or ""
    ], " | ")
    line3 = _join_nonempty([
        "focus: TikTok YouTube reviews, guides, explainers",
        f"concerns: {concerns_kw}" if concerns_kw else "",
        sentiment_prompt_hint or "extract sentiment (positive/negative) and evidence"
    ], " | ")

    # Make a compact multi-line that still works fine as a topic
    topic = "\n".join([p for p in [line1, line2, line3] if p])
    return topic

def build_allow_block(
    allow_domains: Optional[List[str]] = None,
    block_domains: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    return {
        "allow": (allow_domains or DEFAULT_ALLOW),
        "block": (block_domains or DEFAULT_BLOCK),
    }

def make_websearch_request(
    *,
    age: Optional[int] = None,
    town: Optional[str] = None,
    flat_type: Optional[str] = None,
    launch_month: Optional[str] = None,
    budget_sgd: Optional[int] = None,
    concerns: Optional[List[str]] = None,
    perspective: Optional[str] = None,
    sentiment_prompt_hint: Optional[str] = None,
    max_results: int = 10,
    allow_domains: Optional[List[str]] = None,
    block_domains: Optional[List[str]] = None,
    llm: Optional[str] = None,                 # "claude" or "nova" to rewrite topic
    model_id_override: Optional[str] = None,   # explicit Bedrock model id
    bedrock_region: Optional[str] = None,      # defaults to env or us-east-1
    system_prompt: Optional[str] = None,       # custom system prompt for LLM rewrite
) -> Dict[str, Any]:
    """
    Returns kwargs you can pass straight into your orchestrator (topic mode),
    or into process_websearch() if you want to call it directly.
    """
    topic = build_topic_from_params(
        age=age, town=town, flat_type=flat_type, launch_month=launch_month,
        budget_sgd=budget_sgd, concerns=concerns, perspective=perspective,
        sentiment_prompt_hint=sentiment_prompt_hint
    )
    # Optionally refine topic with Bedrock LLM (Nova only)
    if llm is not None:  # any value triggers rewrite, coerced to nova
        print("nova connected")
        if QB_DEBUG:
            print("[QB] Rewriting topic with Nova …")
        answer = rewrite_topic_with_llm(
            topic,
            llm="nova",
            model_id=_resolve_model_id("nova", model_id_override),
            region=bedrock_region,
            system_prompt=system_prompt,
        )
        if QB_DEBUG and topic:
            print("[QB] Final topic:", topic)
    ab = build_allow_block(allow_domains, block_domains)
    return {
        "topic": answer,
        "web_max_results": max_results,
        "web_allow_domains": ab["allow"],
        "web_block_domains": ab["block"],
    }


if __name__ == "__main__":
    os.environ.setdefault("QB_DEBUG", "1")
    req2 = make_websearch_request(
        age=29, town="Toa Payoh", flat_type="4-room",
        launch_month="July 2025", concerns=["MRT","schools","resale value"],
        llm="nova",
        system_prompt=""
    )
    print("\n[LLM topic]", req2['topic'])