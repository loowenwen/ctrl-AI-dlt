# file: lambda_handler.py
from orchestrator import run_orchestrator

def handler(event, context):
    """
    event example:
    {
      "topic": "...",                 # OR
      "query": "...",                 # OR
      "query_params": {...},
      "urls": ["..."],
      "web_max_results": 10,
      "top_discover": 10,
      "parallel_videos": True,
      "max_workers": 4,
      "return_transcript": False,
      "run_sentiment": True,
      "use_query_builder": True
    }
    """
    # Let orchestrator validate/synthesize topic as you already implemented
    out = run_orchestrator(
        topic=event.get("topic"),
        query=event.get("query"),
        urls=event.get("urls"),
        query_params=event.get("query_params"),
        use_query_builder=bool(event.get("use_query_builder", True)),
        top_discover=int(event.get("top_discover", 10)),
        web_max_results=int(event.get("web_max_results", 10)),
        web_allow_domains=event.get("web_allow_domains"),
        web_block_domains=event.get("web_block_domains"),
        parallel_videos=bool(event.get("parallel_videos", True)),
        max_workers=int(event.get("max_workers", 4)),
        video_prompt=event.get("video_prompt") or "Summarize key points, locations, dates, figures, and caveats in bullet points. Highlight the positives and negatives.",
        return_transcript=bool(event.get("return_transcript", False)),
        run_sentiment=bool(event.get("run_sentiment", True)),
    )
    return out