import datetime, sys

def log(msg: str):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    print(f"[{ts}] {msg}", file=sys.stdout, flush=True)
