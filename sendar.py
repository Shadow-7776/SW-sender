#!/usr/bin/env python3
# ============================================================
#  SW MONARCH - API LOOP ENGINE
#  Dev        : SW MONARCH
#  Platform   : Termux / Linux / any Python 3.7+
#  Deps       : none (stdlib only)
#  Disclaimer : Educational / research tool. Do not use
#               against systems or individuals without
#               explicit permission. Not for personal use.
# ============================================================

import os, sys, json, time, threading, urllib.request, urllib.error
from datetime import datetime

# ---------- THEME ----------
G  = "\033[92m"   # bright green
C  = "\033[96m"   # cyan
Y  = "\033[93m"   # yellow
R  = "\033[91m"   # red
D  = "\033[90m"   # dark grey
B  = "\033[1m"    # bold
X  = "\033[0m"    # reset

LOCK = threading.Lock()
LOG_PATH = os.path.expanduser("~/.sw_monarch.log")

# ---------- ENDPOINT POOL (public, keyless) ----------
ENDPOINTS = [
    ("Chuck Norris",  "https://api.chucknorris.io/jokes/random"),
    ("Official Joke", "https://official-joke-api.appspot.com/random_joke"),
    ("Dog CEO",       "https://dog.ceo/api/breeds/image/random"),
    ("Cat Fact",      "https://catfact.ninja/fact"),
    ("Zen Quotes",    "https://zenquotes.io/api/random"),
    ("GitHub Zen",    "https://api.github.com/zen"),
    ("IP Echo",       "https://api.ipify.org?format=json"),
    ("HTTPBin",       "https://httpbin.org/get"),
    ("CoinGecko BTC", "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"),
    ("SpaceX Latest", "https://api.spacexdata.com/v4/launches/latest"),
]

# ---------- CORE ----------
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def out(text, end="\n"):
    with LOCK:
        sys.stdout.write(text + end)
        sys.stdout.flush()

def ts():
    return datetime.now().strftime("%H:%M:%S")

def summarize(raw):
    try:
        data = json.loads(raw)
    except Exception:
        return raw[:100].replace("\n", " ")
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict):
        for k in ("value", "fact", "joke", "zen", "text", "setup",
                  "name", "message", "content", "url", "quote"):
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()[:100]
        return json.dumps(data)[:100]
    return str(data)[:100]

def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={
        "User-Agent": "SW-MONARCH/1.0 (educational)",
        "Accept": "application/json, text/plain, */*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def log(line):
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ---------- WORKER ----------
class Engine:
    def __init__(self, threads=4, interval=1.0, max_cycles=0):
        self.threads = threads
        self.interval = interval
        self.max_cycles = max_cycles
        self.running = False
        self.idx = 0
        self.stats = {"ok": 0, "err": 0, "total": 0}
        self.start = None

    def _next(self):
        with LOCK:
            ep = ENDPOINTS[self.idx % len(ENDPOINTS)]
            self.idx += 1
        return ep

    def _worker(self, wid):
        backoff = 1.0
        cycles = 0
        while self.running:
            if self.max_cycles and cycles >= self.max_cycles:
                return
            cycles += 1
            name, url = self._next()
            t0 = time.time()
            try:
                raw = fetch(url)
                ms = int((time.time() - t0) * 1000)
                info = summarize(raw)
                with LOCK:
                    self.stats["ok"] += 1
                    self.stats["total"] += 1
                out(f"{D}[{ts()}]{X} {G}[OK]{X} {C}w{wid}{X} "
                    f"{B}{name:<14}{X} {D}{ms:>4}ms{X} {D}|{X} {info}")
                log(f"OK {ts()} w{wid} {name} {ms}ms")
                backoff = 1.0
            except Exception as e:
                with LOCK:
                    self.stats["err"] += 1
                    self.stats["total"] += 1
                msg = str(e)[:60] or e.__class__.__name__
                out(f"{D}[{ts()}]{X} {R}[!!]{X} {C}w{wid}{X} "
                    f"{B}{name:<14}{X} {D}|{X} {R}{msg}{X}")
                log(f"ERR {ts()} w{wid} {name} {msg}")
                time.sleep(backoff)
                backoff = min(backoff * 1.6, 10.0)
            time.sleep(self.interval)

    def start_engine(self):
        self.running = True
        self.start = time.time()
        self.stats = {"ok": 0, "err": 0, "total": 0}
        self.idx = 0
        clear()
        banner(small=True)
        out(f"{D}threads={self.threads}  interval={self.interval}s  "
            f"pool={len(ENDPOINTS)}{X}\n")
        workers = [threading.Thread(target=self._worker, args=(i + 1,), daemon=True)
                   for i in range(self.threads)]
        for w in workers:
            w.start()
        try:
            while any(w.is_alive() for w in workers):
                time.sleep(1)
                elapsed = int(time.time() - self.start)
                s = self.stats
                rate = (s["total"] / elapsed) if elapsed else 0
                out(f"\r{D}elapsed {elapsed:>4}s | "
                    f"{G}ok {s['ok']}{X} {D}/{X} {R}err {s['err']}{X} "
                    f"{D}| {rate:.1f} req/s{X}   ", end="")
        except KeyboardInterrupt:
            self.running = False
            out(f"\n\n{Y}[*] Interrupted - draining threads...{X}")
        finally:
            self.running = False
            for w in workers:
                w.join(timeout=2)
            s = self.stats
            out(f"\n{G}[+] Session ended. ok={s['ok']} err={s['err']} "
                f"total={s['total']}{X}")
            out(f"{D}[i] Log: {LOG_PATH}{X}")
            input(f"{D}\nPress ENTER to return to menu...{X}")

# ---------- UI ----------
BANNER = r"""
   _____ __        __  __  ____  _   _  _   _    _    ____  _   _
  / ____|\ \      / / |  \/  |/ __ \| \ | || \ | |  / \  |  _ \| | | |
 | (___   \ \ /\ / /  | \  / | |  | |  \| ||  \| | / _ \ | |_) | | | |
  \___ \   \ V  V /   | |\/| | |  | | . ` || . ` |/ ___ \|  _ <| |_| |
  ____) |   \_/\_/    | |  | | |__| | |\  || |\  / ___ \| |_) |\___/
 |_____/              |_|  |_|\____/|_| \_||_| \_/_/   \_\____/  (API)

            [ A P I   L O O P   E N G I N E ]   v1.0
                  Dev: SW MONARCH   |   Termux
"""

def banner(small=False):
    if small:
        out(f"{G}{B}  >> SW MONARCH // API LOOP ENGINE{X}  {D}threads running{X}\n")
        return
    print(f"{G}{BANNER}{X}")

def disclaimer():
    clear()
    out(f"{R}{B}  DISCLAIMER{X}")
    out(f"{D}  " + "-" * 52 + f"{X}")
    out(f"{Y}  This tool is for educational and research purposes only.{X}")
    out(f"{Y}  It queries public, rate-limited APIs. Do not use it against{X}")
    out(f"{Y}  individuals or systems you do not own or have written{X}")
    out(f"{Y}  permission to test. The author takes no responsibility for{X}")
    out(f"{Y}  misuse.{X}")
    out(f"{D}  " + "-" * 52 + f"{X}")
    input(f"{G}  Press ENTER to acknowledge...{X}")

def show_endpoints():
    clear()
    banner(small=True)
    out(f"{C}  {B}ENDPOINT POOL{X}\n")
    for i, (name, url) in enumerate(ENDPOINTS, 1):
        out(f"  {D}[{i:02d}]{X} {B}{name:<16}{X} {D}{url[:52]}{X}")
    input(f"\n{D}  Press ENTER to return...{X}")

def show_log():
    clear()
    banner(small=True)
    if not os.path.exists(LOG_PATH):
        out(f"{Y}  No log yet.{X}")
    else:
        with open(LOG_PATH) as f:
            lines = f.readlines()[-25:]
        for l in lines:
            out(f"  {D}{l.rstrip()}{X}")
    input(f"\n{D}  Press ENTER to return...{X}")

def settings():
    while True:
        clear()
        banner(small=True)
        out(f"{C}  {B}SETTINGS{X}\n")
        out(f"  {D}[1]{X} Threads       (default 4)")
        out(f"  {D}[2]{X} Interval sec  (default 1.0)")
        out(f"  {D}[3]{X} Max cycles/worker  (0 = infinite)")
        out(f"  {D}[0]{X} Back\n")
        ch = input(f"{G}  > {X}").strip()
        if ch == "0":
            return None
        # simple parsed return of config -> handled in menu
        return ch

def menu():
    cfg = {"threads": 4, "interval": 1.0, "max_cycles": 0}
    while True:
        clear()
        banner()
        out(f"{D}  " + "-" * 56 + f"{X}")
        out(f"  {G}[1]{X} {B}Start API Loop{X}       {D}-> {cfg['threads']} threads, "
            f"{cfg['interval']}s interval{X}")
        out(f"  {G}[2]{X} {B}View Endpoints{X}      {D}({len(ENDPOINTS)} in pool){X}")
        out(f"  {G}[3]{X} {B}Configure{X}")
        out(f"  {G}[4]{X} {B}View Log{X}             {D}{LOG_PATH}{X}")
        out(f"  {G}[0]{X} {B}Exit{X}")
        out(f"{D}  " + "-" * 56 + f"{X}")
        ch = input(f"{G}  select > {X}").strip()

        if ch == "1":
            Engine(cfg["threads"], cfg["interval"], cfg["max_cycles"]).start_engine()
        elif ch == "2":
            show_endpoints()
        elif ch == "3":
            while True:
                clear()
                banner(small=True)
                out(f"{C}  {B}CONFIGURE{X}\n")
                out(f"  {D}[1]{X} Threads         {G}{cfg['threads']}{X}")
                out(f"  {D}[2]{X} Interval (sec)  {G}{cfg['interval']}{X}")
                out(f"  {D}[3]{X} Max cycles      {G}{cfg['max_cycles']}{X}  {D}(0=infinite){X}")
                out(f"  {D}[0]{X} Back\n")
                c2 = input(f"{G}  > {X}").strip()
                if c2 == "0":
                    break
                try:
                    if c2 == "1":
                        cfg["threads"] = max(1, min(32, int(input("  threads: "))))
                    elif c2 == "2":
                        cfg["interval"] = max(0.0, float(input("  interval: ")))
                    elif c2 == "3":
                        cfg["max_cycles"] = max(0, int(input("  max cycles: ")))
                except ValueError:
                    out(f"{R}  invalid input{X}")
                    time.sleep(1)
        elif ch == "4":
            show_log()
        elif ch == "0":
            clear()
            out(f"{G}  SW MONARCH - signing off. Stay curious.{X}\n")
            sys.exit(0)

# ---------- ENTRY ----------
if __name__ == "__main__":
    try:
        disclaimer()
        menu()
    except KeyboardInterrupt:
        out(f"\n{Y}  aborted.{X}")
        sys.exit(0)
