import re
import httpx

_client = None


def _get_active_window_title():
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception:
        return ""


def _pick_profile(cfg):
    llm = cfg.get("llm", {})
    profiles = llm.get("profiles", {})
    default = llm.get("default_profile", "general")
    title = _get_active_window_title()
    if title:
        for rule in llm.get("auto_match", []):
            if re.search(rule["pattern"], title, re.IGNORECASE):
                name = rule["profile"]
                if name in profiles:
                    return name, profiles[name]["prompt"]
    if default in profiles:
        return default, profiles[default]["prompt"]
    return "general", llm.get("prompt", "")


def _headers(cfg):
    key = cfg.get("llm", {}).get("api_key", "")
    return {"Authorization": f"Bearer {key}"} if key else {}


def _strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def preload(cfg):
    global _client
    llm = cfg.get("llm", {})
    if not llm.get("enabled"):
        return
    _client = httpx.Client(timeout=60)
    print(f"[LLM] {llm['model']}")


def polish(text, cfg):
    global _client
    llm = cfg.get("llm", {})
    if not llm.get("enabled"):
        return text
    profile_name, prompt = _pick_profile(cfg)
    try:
        if _client is None:
            _client = httpx.Client(timeout=60)
        import time
        t0 = time.perf_counter()
        resp = _client.post(
            llm["api_url"],
            headers=_headers(cfg),
            json={
                "model": llm["model"],
                "messages": [{"role": "user", "content": prompt + text}],
                "temperature": 0,
            },
            timeout=60,
        )
        resp.raise_for_status()
        elapsed = time.perf_counter() - t0
        result = _strip_think(resp.json()["choices"][0]["message"]["content"])
        print(f"[LLM] {llm['model']}|{profile_name} ({elapsed:.2f}s) {result}")
        return result
    except Exception as e:
        print(f"[LLM] 失败: {e}")
        return text
