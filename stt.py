import base64
import hashlib
import hmac
import io
import importlib.util
import json
import logging
import os
import sys
import time
import wave
from datetime import datetime, timezone

import httpx
import numpy as np
import opencc

log = logging.getLogger("voice")


def _setup_nvidia_dll_path():
    """Windows: 将 pip 安装的 nvidia dll 路径加入搜索路径"""
    for pkg in ("nvidia.cublas", "nvidia.cudnn"):
        spec = importlib.util.find_spec(pkg)
        if not spec or not spec.submodule_search_locations:
            continue
        for loc in spec.submodule_search_locations:
            for sub in ("bin", "lib", ""):
                d = os.path.join(loc, sub) if sub else loc
                if os.path.isdir(d):
                    os.add_dll_directory(d)
                    os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


if sys.platform == "win32":
    _setup_nvidia_dll_path()

_model = None
_t2s = opencc.OpenCC("t2s")
_PUNCT_MAP = str.maketrans({
    ",": "，", ".": "。", "?": "？", "!": "！",
    ":": "：", ";": "；", "(": "（", ")": "）",
})


def _fix_punct(text):
    return text.translate(_PUNCT_MAP)


def _is_silent(wav_bytes, threshold=0.01):
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32767
        return np.sqrt(np.mean(audio ** 2)) < threshold


def _get_model(cfg):
    global _model
    if _model is None:
        local = cfg["stt"]["local"]
        device = local.get("device", "cuda")
        model = local.get("model", "large-v3")
        log.info(f"[STT] 加载 {model} (device={device})...")
        from faster_whisper import WhisperModel
        _model = WhisperModel(model, device=device, compute_type="auto")
        log.info(f"[STT] 就绪 ({model}, {device})")
    return _model


def _tc3_sign(secret_key, payload_str, timestamp):
    """腾讯云 TC3-HMAC-SHA256 签名"""
    service = "asr"
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    credential_scope = f"{date}/{service}/tc3_request"
    canonical = (f"POST\n/\n\ncontent-type:application/json; charset=utf-8\n"
                 f"host:asr.tencentcloudapi.com\n\ncontent-type;host\n"
                 f"{hashlib.sha256(payload_str.encode()).hexdigest()}")
    string_to_sign = (f"TC3-HMAC-SHA256\n{timestamp}\n{credential_scope}\n"
                      f"{hashlib.sha256(canonical.encode()).hexdigest()}")

    def _hmac_sha256(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    key = _hmac_sha256(("TC3" + secret_key).encode(), date)
    key = _hmac_sha256(key, service)
    key = _hmac_sha256(key, "tc3_request")
    signature = hmac.new(key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    return signature, credential_scope


# ── preload / unload ──

def preload(cfg):
    engine = cfg["stt"]["engine"]
    if engine == "local":
        _get_model(cfg)
    elif engine == "tencent":
        tc = cfg["stt"].get("tencent", {})
        if not tc.get("secret_id") or not tc.get("secret_key"):
            log.error("[STT] 腾讯云 ASR 未配置 secret_id/secret_key，请编辑 config.yaml")
            sys.exit(1)
    log.info(f"[STT] engine={engine}")


def unload():
    global _model
    if _model is not None:
        del _model
        _model = None


# ── transcribe ──

def transcribe_local(wav_bytes, cfg):
    model = _get_model(cfg)
    local = cfg["stt"]["local"]
    words = [w for w in local.get("dictionary", []) if w]
    prompt = "，".join(words) if words else None
    segments, _ = model.transcribe(
        io.BytesIO(wav_bytes), language=local.get("language", "zh"), initial_prompt=prompt)
    return "".join(s.text for s in segments).strip()


def transcribe_tencent(wav_bytes, cfg):
    tc = cfg["stt"]["tencent"]
    payload = {
        "EngSerViceType": tc.get("engine_type", "16k_zh"),
        "SourceType": 1,
        "VoiceFormat": "wav",
        "Data": base64.b64encode(wav_bytes).decode(),
        "DataLen": len(wav_bytes),
    }
    words = [w for w in cfg["stt"].get("local", {}).get("dictionary", []) if w]
    if words:
        payload["HotwordList"] = ",".join(f"{w}|10" for w in words)

    payload_str = json.dumps(payload)
    timestamp = int(time.time())
    signature, scope = _tc3_sign(tc["secret_key"], payload_str, timestamp)
    host = "asr.tencentcloudapi.com"

    resp = httpx.post(
        f"https://{host}",
        headers={
            "Authorization": f"TC3-HMAC-SHA256 Credential={tc['secret_id']}/{scope}, SignedHeaders=content-type;host, Signature={signature}",
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "X-TC-Action": "SentenceRecognition",
            "X-TC-Version": "2019-06-14",
            "X-TC-Timestamp": str(timestamp),
        },
        content=payload_str,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if "Response" in result and "Result" in result["Response"]:
        return result["Response"]["Result"].strip()
    err = result.get("Response", {}).get("Error", {})
    raise RuntimeError(f"腾讯云ASR错误: {err.get('Code')} {err.get('Message')}")


_TRANSCRIBERS = {"local": transcribe_local, "tencent": transcribe_tencent}


def transcribe(wav_bytes, cfg):
    if _is_silent(wav_bytes):
        log.info("[STT] 跳过静音")
        return ""
    t0 = time.perf_counter()
    fn = _TRANSCRIBERS[cfg["stt"]["engine"]]
    for attempt in range(2):
        try:
            text = fn(wav_bytes, cfg)
            break
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            if attempt == 0:
                log.info(f"[STT] 连接失败，重试: {e}")
                continue
            raise
    log.info(f"[STT] ({time.perf_counter() - t0:.2f}s) {text}")
    return _fix_punct(_t2s.convert(text))
