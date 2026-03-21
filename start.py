"""
╔══════════════════════════════════════════════════════════════╗
║                Agora AI — Unified Launcher                   ║
║  Checks deps → checks Ollama → maps models → starts app      ║
║  Press Ctrl+C to shut everything down cleanly                ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python start.py
"""

import sys
import os
import subprocess
import time
import signal
import threading
import http.server
import socketserver
import urllib.request
import json
import webbrowser

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
BACKEND_PORT  = 8080
FRONTEND_PORT = 5173
OLLAMA_HOST   = "http://localhost:11434"
PROJECT_ROOT  = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR  = os.path.join(PROJECT_ROOT, "frontend")
REQUIREMENTS  = os.path.join(PROJECT_ROOT, "requirements.txt")

# Each agent's preferred model name (exact or base match against what Ollama has)
REQUIRED_MODELS = [
    ("gemma2:2b",     "⚖️  Ethical Agent   — Gemma 2 (2B) by Google"),
    ("llama3.2:3b",   "📜 Legal Agent     — Llama 3.2 (3B) by Meta"),
    ("mistral:latest","🤝 Social Agent    — Mistral 7B by Mistral AI"),
    ("qwen2.5:3b",    "📈 Economic Agent  — Qwen 2.5 (3B) by Alibaba"),
    ("phi3.5:mini",   "🏛️  Consensus Agent — Phi-3.5 Mini by Microsoft"),
]

# ─────────────────────────────────────────────────────────────
# Globals
# ─────────────────────────────────────────────────────────────
_backend_proc    = None
_frontend_server = None
_frontend_thread = None
_shutdown_flag   = threading.Event()


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def banner(text, char="─", width=62):
    print(f"\n{char * width}")
    print(f"  {text}")
    print(char * width)

def ok(msg):   print(f"  ✅  {msg}")
def warn(msg): print(f"  ⚠️   {msg}")
def info(msg): print(f"  ℹ️   {msg}")
def err(msg):  print(f"  ❌  {msg}")
def step(msg): print(f"\n  ▶  {msg}")


# ─────────────────────────────────────────────────────────────
# Step 1 — Python package check & auto-install if missing
# ─────────────────────────────────────────────────────────────
IMPORT_ALIASES = {
    "sse_starlette": "sse_starlette",
    "uvicorn":       "uvicorn",
    "ollama":        "ollama",
    "pydantic":      "pydantic",
    "fastapi":       "fastapi",
    "httpx":         "httpx",
    "pyyaml":        "yaml",
}

def _try_import(name):
    import importlib.util
    mod = IMPORT_ALIASES.get(name, name)
    return importlib.util.find_spec(mod) is not None

def check_and_install_packages():
    banner("Step 1 / 4 — Python Package Check")

    if not os.path.exists(REQUIREMENTS):
        warn("requirements.txt not found — skipping.")
        return

    with open(REQUIREMENTS) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    missing = []
    for line in lines:
        pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].strip()
        pkg_name = pkg.split("[")[0].lower().replace("-", "_")
        if _try_import(pkg_name):
            ok(f"{pkg} — installed")
        else:
            warn(f"{pkg} — missing, will install")
            missing.append(line)

    if missing:
        step(f"Installing {len(missing)} missing package(s)...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + missing,
            capture_output=False,
        )
        if result.returncode == 0:
            ok("All packages installed")
        else:
            err("Some packages failed — app may not work correctly")
    else:
        ok("All required packages are present")


# ─────────────────────────────────────────────────────────────
# Step 2 — Ollama service check
# ─────────────────────────────────────────────────────────────
def check_ollama_running():
    banner("Step 2 / 4 — Ollama Service Check")
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                ok("Ollama is running")
                return True
    except Exception:
        pass

    warn("Ollama is not reachable at localhost:11434")
    print()
    print("  Make sure Ollama is running:   ollama serve")
    print("  Download it from:              https://ollama.com")
    print()
    answer = input("  Continue anyway? (y/N): ").strip().lower()
    return answer == "y"


# ─────────────────────────────────────────────────────────────
# Step 3 — Check which required models are already installed
#           NO downloading — reads from Ollama as-is
# ─────────────────────────────────────────────────────────────
def check_models():
    banner("Step 3 / 4 — Ollama Model Check  (using installed models only)")

    # Fetch the list of locally installed models from Ollama
    installed = {}        # model_name -> size_gb
    installed_names = []  # ordered list for matching
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            for m in data.get("models", []):
                name = m.get("name", "")
                size_gb = m.get("size", 0) / (1024 ** 3)
                installed[name] = size_gb
                installed_names.append(name)
    except Exception as e:
        warn(f"Could not fetch model list from Ollama: {e}")
        return

    if not installed:
        warn("No models found in Ollama at all.")
        info("Pull a model first:  ollama pull <model-name>")
        return

    # Show all installed models
    info(f"{len(installed)} model(s) already installed in Ollama:")
    for name, gb in installed.items():
        print(f"       • {name}  ({gb:.1f} GB)")
    print()

    def find_match(model_name):
        """Exact match first; fall back to same base name with any tag."""
        if model_name in installed:
            return model_name
        base = model_name.split(":")[0].lower()
        for n in installed_names:
            if n.split(":")[0].lower() == base:
                return n
        return None

    # Map each agent to whatever is installed
    missing_agents = []
    for model, desc in REQUIRED_MODELS:
        match = find_match(model)
        if match:
            note = f"  →  using '{match}'" if match != model else ""
            ok(f"{desc}{note}")
        else:
            warn(f"{desc}  ←  NOT found in Ollama")
            missing_agents.append(model)

    if missing_agents:
        print()
        warn(f"{len(missing_agents)} model(s) not found locally — those agents will fail at runtime.")
        info("To add them, run in another terminal:")
        for m in missing_agents:
            print(f"       ollama pull {m}")


# ─────────────────────────────────────────────────────────────
# Step 4a — Start the FastAPI backend (uvicorn)
# ─────────────────────────────────────────────────────────────
def start_backend():
    global _backend_proc
    banner("Step 4 / 4 — Starting Servers")
    step(f"Backend  (FastAPI + Uvicorn) → http://localhost:{BACKEND_PORT}")

    _backend_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", str(BACKEND_PORT),
            "--reload",
        ],
        cwd=PROJECT_ROOT,
    )
    time.sleep(2.5)
    if _backend_proc.poll() is not None:
        err("Backend failed to start — check the error above.")
        sys.exit(1)
    ok(f"Backend  running  (PID {_backend_proc.pid})")


# ─────────────────────────────────────────────────────────────
# Step 4b — Start the frontend HTTP server (in a thread)
# ─────────────────────────────────────────────────────────────
class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the frontend folder without per-request log noise."""
    def log_message(self, format, *args): pass   # noqa
    def log_error(self, format, *args):   pass   # noqa


def start_frontend():
    global _frontend_server, _frontend_thread

    step(f"Frontend (HTTP server)         → http://localhost:{FRONTEND_PORT}")

    os.chdir(FRONTEND_DIR)
    _frontend_server = socketserver.TCPServer(
        ("", FRONTEND_PORT), _SilentHandler, bind_and_activate=False
    )
    _frontend_server.allow_reuse_address = True
    _frontend_server.server_bind()
    _frontend_server.server_activate()

    _frontend_thread = threading.Thread(
        target=_frontend_server.serve_forever, daemon=True
    )
    _frontend_thread.start()
    ok(f"Frontend running  → http://localhost:{FRONTEND_PORT}")

    # Auto-open the browser once the frontend is confirmed running
    time.sleep(0.5)   # small grace period so the server is fully bound
    webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
    ok("Browser opened  → Agora AI")


# ─────────────────────────────────────────────────────────────
# Graceful shutdown
# ─────────────────────────────────────────────────────────────
def shutdown(signum=None, frame=None):
    if _shutdown_flag.is_set():
        return
    _shutdown_flag.set()

    print()
    banner("Shutting Down Agora AI", "═")

    if _backend_proc and _backend_proc.poll() is None:
        step("Stopping backend...")
        _backend_proc.terminate()
        try:
            _backend_proc.wait(timeout=5)
            ok("Backend stopped")
        except subprocess.TimeoutExpired:
            _backend_proc.kill()
            ok("Backend force-killed")

    if _frontend_server:
        step("Stopping frontend server...")
        _frontend_server.shutdown()
        ok("Frontend stopped")

    print()
    print("  👋  Agora AI has exited. Goodbye!\n")
    sys.exit(0)


signal.signal(signal.SIGINT,  shutdown)
signal.signal(signal.SIGTERM, shutdown)
if hasattr(signal, "SIGBREAK"):      # Windows Ctrl+Break
    signal.signal(signal.SIGBREAK, shutdown)


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║             🧠  Agora AI — Unified Launcher                  ║")
    print("║      Multi-Agent Debate Engine · 5 Free Local LLMs         ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Pre-flight checks
    check_and_install_packages()

    ollama_ok = check_ollama_running()
    if ollama_ok:
        check_models()          # read-only: no downloads
    else:
        info("Skipping model checks — Ollama not available.")

    # Start both servers
    start_backend()
    start_frontend()

    # Print the ready banner
    print()
    print("═" * 62)
    print()
    print("  🚀  Agora AI is LIVE!")
    print()
    print(f"  🌐  Open your browser → http://localhost:{FRONTEND_PORT}")
    print(f"  🔧  Backend API docs  → http://localhost:{BACKEND_PORT}/docs")
    print()
    print("  Agent Models (from your Ollama library):")
    print("    ⚖️  Ethical     → gemma2:2b        (Google)")
    print("    📜 Legal       → llama3.2:3b      (Meta)")
    print("    🤝 Social      → mistral:latest   (Mistral AI)")
    print("    📈 Economic    → qwen2.5:3b       (Alibaba)")
    print("    🏛️  Consensus   → phi3.5:mini      (Microsoft)")
    print()
    print("  Press Ctrl+C to stop everything and exit cleanly.")
    print()
    print("═" * 62)

    # Keep the main thread alive; auto-restart backend if it dies
    try:
        while not _shutdown_flag.is_set():
            if _backend_proc and _backend_proc.poll() is not None:
                warn("Backend exited unexpectedly — restarting...")
                start_backend()
            time.sleep(2)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
