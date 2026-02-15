import json
import time
from dataclasses import dataclass
from django.conf import settings
import redis

def rds():
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

CALLS_KEY = "voipportal:active_calls"  # hash: call_id -> json
CALLS_INDEX = "voipportal:active_calls:index"  # set of call_ids

def upsert_call(call_id: str, payload: dict):
    payload["updated_at"] = int(time.time())
    cli = rds()
    cli.hset(CALLS_KEY, call_id, json.dumps(payload, ensure_ascii=False))
    cli.sadd(CALLS_INDEX, call_id)

def remove_call(call_id: str):
    cli = rds()
    cli.hdel(CALLS_KEY, call_id)
    cli.srem(CALLS_INDEX, call_id)

def list_calls():
    cli = rds()
    ids = list(cli.smembers(CALLS_INDEX))
    out = []
    if not ids:
        return out
    vals = cli.hmget(CALLS_KEY, ids)
    for v in vals:
        if not v:
            continue
        try:
            out.append(json.loads(v))
        except Exception:
            pass
    # sort by start_ts desc
    out.sort(key=lambda x: x.get("start_ts", 0), reverse=True)
    return out
