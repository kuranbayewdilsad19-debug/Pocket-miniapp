from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import time, random, threading
from threading import Lock

app = FastAPI()
app.mount("/web", StaticFiles(directory="web"), name="web")

# ---- In-memory storage (demo) ----
lock = Lock()
history = []  # list of dicts
next_id = 1
PAIR_DEFAULT = "EURUSD"
RESOLVE_SEC = 60
MAX_HISTORY = 20

def clamp(x, a, b):
    return max(a, min(b, x))

def compute_confidence(rsi_val: float) -> int:
    """
    Confidence = RSI qanchalik ekstremal bo‘lsa shunchalik yuqori (demo).
    50..95 orasida.
    """
    dist = abs(rsi_val - 50.0)  # 0..50
    conf = 50 + (dist / 50.0) * 45  # 50..95
    return int(round(clamp(conf, 50, 95)))

def compute_signal_from_rsi(rsi_val: float) -> str:
    if rsi_val >= 70:
        return "SELL"
    if rsi_val <= 30:
        return "BUY"
    return "WAIT"

def resolve_signal(signal_id: int):
    """
    60 sekunddan keyin pending signalni win/loss qilib qo‘yadi (demo).
    Win ehtimoli confidence/100 ga bog‘liq.
    """
    with lock:
        item = next((x for x in history if x["id"] == signal_id), None)
        if not item or item["status"] != "PENDING":
            return
        p_win = item["confidence"] / 100.0
        win = (random.random() < p_win)
        item["status"] = "WIN" if win else "LOSS"
        item["result_symbol"] = "✅" if win else "❌"
        item["result_sign"] = "+" if win else "-"
        item["resolved_at"] = int(time.time())

def stats_last20():
    last = history[:MAX_HISTORY]
    wins = sum(1 for x in last if x["status"] == "WIN")
    losses = sum(1 for x in last if x["status"] == "LOSS")
    done = wins + losses
    acc = int(round((wins / done) * 100)) if done else 0
    return wins, losses, acc

@app.get("/")
def root():
    return {"ok": True}

@app.get("/api/signal")
def api_signal(pair: str = PAIR_DEFAULT):
    """
    Signal yaratadi (demo RSI + demo confidence)
    va 60s dan keyin natijani resolve qiladi.
    """
    global next_id

    # demo RSI: 10..95 oralig‘ida random (xohlasang keyin real data qo‘shamiz)
    rsi_val = round(random.uniform(10, 95), 2)
    sig = compute_signal_from_rsi(rsi_val)
    conf = compute_confidence(rsi_val)

    now = int(time.time())

    with lock:
        sid = next_id
        next_id += 1

        item = {
            "id": sid,
            "time": now,
            "pair": pair.upper(),
            "tf": "M1",
            "rsi": rsi_val,
            "signal": sig,
            "confidence": conf,
            "status": "PENDING",      # PENDING -> WIN/LOSS
            "result_symbol": "⏳",
            "result_sign": "",
            "resolved_at": None
        }

        # newest first
        history.insert(0, item)
        # keep only last 20
        del history[MAX_HISTORY:]

    # start timer to resolve without blocking
    threading.Timer(RESOLVE_SEC, resolve_signal, args=(sid,)).start()

    # accuracy now (last 20 resolved)
    with lock:
        wins, losses, acc = stats_last20()

    return {
        "ok": True,
        "id": sid,
        "pair": item["pair"],
        "tf": item["tf"],
        "rsi": item["rsi"],
        "signal": item["signal"],
        "confidence": item["confidence"],
        "accuracy_last20": acc,
        "wins_last20": wins,
        "losses_last20": losses,
        "resolve_in_sec": RESOLVE_SEC
    }

@app.get("/api/history")
def api_history():
    with lock:
        last = history[:MAX_HISTORY]
        wins, losses, acc = stats_last20()
        return {
            "ok": True,
            "wins": wins,
            "losses": losses,
            "accuracy": acc,
            "items": last
        }
