# router_lambda.py
import json, os, boto3

L = boto3.client("lambda")

def lambda_handler(event, _ctx):
    discover_evt = event.get("discover", {})
    d = L.invoke(
        FunctionName=os.environ["DISCOVER_LAMBDA_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps(discover_evt).encode("utf-8"),
    )
    discover_out = json.load(d["Payload"])  # assumes {"ok": true, "data": {...}}

    items = discover_out["data"]["items"]
    results = []
    for it in items:
        # fan-out (serial here; for concurrency use async InvocationType="Event" + queue)
        vi_evt = {"mode": "transcribe_to_text", "input": it["url"], "prompt": "Your prompt"}
        v = L.invoke(FunctionName=os.environ["VIDEO_LAMBDA_ARN"], InvocationType="RequestResponse",
                     Payload=json.dumps(vi_evt).encode("utf-8"))
        v_out = json.load(v["Payload"])

        wa_evt = {"mode": "topic", "topic": it.get("caption","")}
        w = L.invoke(FunctionName=os.environ["WEB_LAMBDA_ARN"], InvocationType="RequestResponse",
                     Payload=json.dumps(wa_evt).encode("utf-8"))
        w_out = json.load(w["Payload"])

        results.append({"item": it, "video": v_out, "web": w_out})

    # Aggregate result
    return {"ok": True, "data": {"results": results}}