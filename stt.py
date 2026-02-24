import logging
import io
import platform
import sys
log = logging.getLogger("voice")
import wave
import httpx
import opencc
import numpy as np

_model = None
_t2s = opencc.OpenCC("t2s")

_PUNCT_MAP = str.maketrans({
    ",": "，", ".": "。", "?": "？", "!": "！",
    ":": "：", ";": "；", "(": "（", ")": "）",
})


def _fix_punct(text):
    return text.translate(_PUNCT_MAP)


def _is_silent(wav_bytes, threshold=0.01):
    """检测音频是否为静音"""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767
        return np.sqrt(np.mean(audio ** 2)) < threshold


def _detect_cuda():
    """检测 CUDA 是否真正可用"""
    if platform.system() != "Windows":
        return False
    try:
        import ctranslate2
        if "cuda" in ctranslate2.get_supported_compute_types("cuda"):
            log.info("[STT] CUDA 可用 (ctranslate2)")
            return True
    except Exception as e:
        log.info(f"[STT] ctranslate2 CUDA 检测失败: {e}")
    try:
        import ctypes
        ctypes.cdll.LoadLibrary("nvcuda.dll")
        log.info("[STT] CUDA 可用 (nvcuda.dll)")
        return True
    except OSError:
        pass
    return False


def _get_model(cfg):
    global _model
    if _model is None:
        local = cfg["stt"]["local"]
        device = local.get("device", "cuda")
        model = local.get("model", "large-v3")
        log.info(f"[STT] 加载 {model} (device={device})...")
        if platform.system() == "Windows" and device == "cuda":
            import os, importlib.util
            for lib in ("nvidia.cublas", "nvidia.cudnn"):
                spec = importlib.util.find_spec(lib)
                if spec and spec.submodule_search_locations:
                    for loc in spec.submodule_search_locations:
                        dll_dir = os.path.join(loc, "bin")
                        if os.path.isdir(dll_dir):
                            os.add_dll_directory(dll_dir)
                            log.info(f"[STT] 添加 DLL 路径: {dll_dir}")
        from faster_whisper import WhisperModel
        _model = WhisperModel(model, device=device, compute_type="auto")
        log.info(f"[STT] 就绪 ({model}, {device})")
    return _model


def preload(cfg):
    if cfg["stt"]["engine"] == "local":
        local = cfg["stt"]["local"]
        device = local.get("device", "auto")
        model = local.get("model", "auto")
        if device == "auto" or model == "auto":
            if _detect_cuda():
                local["device"] = "cuda" if device == "auto" else device
                local["model"] = "large-v3" if model == "auto" else model
            else:
                log.info("[STT] 无可用 CUDA，切换到腾讯云")
                cfg["stt"]["engine"] = "tencent"
        if cfg["stt"]["engine"] == "local":
            try:
                _get_model(cfg)
            except Exception as e:
                log.info(f"[STT] 本地模型加载失败: {e}，切换到腾讯云")
                cfg["stt"]["engine"] = "tencent"
    if cfg["stt"]["engine"] == "tencent":
        tc = cfg["stt"].get("tencent", {})
        if not tc.get("secret_id") or not tc.get("secret_key"):
            log.error("[STT] 腾讯云 ASR 未配置 secret_id/secret_key，请编辑 config.yaml")
            sys.exit(1)
    if cfg["stt"]["engine"] == "remote":
        remote = cfg["stt"].get("remote", {})
        if not remote.get("api_key"):
            log.error("[STT] 远程 STT 未配置 api_key，请编辑 config.yaml")
            sys.exit(1)
    log.info(f"[STT] engine={cfg['stt']['engine']}")


def unload():
    global _model
    if _model is not None:
        del _model
        _model = None


def transcribe_local(wav_bytes, cfg):
    model = _get_model(cfg)
    local = cfg["stt"]["local"]
    lang = local.get("language", "zh")
    words = [w for w in local.get("dictionary", []) if w]
    prompt = "，".join(words) if words else None
    segments, _ = model.transcribe(io.BytesIO(wav_bytes), language=lang, initial_prompt=prompt)
    return "".join(s.text for s in segments).strip()


def transcribe_remote(wav_bytes, cfg):
    remote = cfg["stt"]["remote"]
    resp = httpx.post(
        remote["api_url"],
        headers={"Authorization": f"Bearer {remote['api_key']}"},
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        data={"model": remote["model"], "language": cfg["stt"]["local"].get("language", "zh")},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["text"].strip()


def transcribe_tencent(wav_bytes, cfg):
    import base64
    import hashlib
    import hmac
    import time as _time
    from datetime import datetime, timezone

    tc = cfg["stt"]["tencent"]
    secret_id = tc["secret_id"]
    secret_key = tc["secret_key"]
    engine = tc.get("engine_type", "16k_zh")

    # 请求体
    data_b64 = base64.b64encode(wav_bytes).decode()
    payload = {
        "EngSerViceType": engine,
        "SourceType": 1,
        "VoiceFormat": "wav",
        "Data": data_b64,
        "DataLen": len(wav_bytes),
    }
    words = cfg["stt"].get("local", {}).get("dictionary", [])
    if words:
        hotwords = ",".join(f"{w}|10" for w in words if w)
        if hotwords:
            payload["HotwordList"] = hotwords

    import json
    payload_str = json.dumps(payload)

    # TC3 签名
    service = "asr"
    host = "asr.tencentcloudapi.com"
    action = "SentenceRecognition"
    version = "2019-06-14"
    timestamp = int(_time.time())
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

    # 1. 拼接规范请求串
    canonical = f"POST\n/\n\ncontent-type:application/json; charset=utf-8\nhost:{host}\n\ncontent-type;host\n{hashlib.sha256(payload_str.encode()).hexdigest()}"
    # 2. 拼接待签名字符串
    credential_scope = f"{date}/{service}/tc3_request"
    string_to_sign = f"TC3-HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical.encode()).hexdigest()}"
    # 3. 计算签名
    def _hmac(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()
    secret_date = _hmac(("TC3" + secret_key).encode(), date)
    secret_service = _hmac(secret_date, service)
    secret_signing = _hmac(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    auth = f"TC3-HMAC-SHA256 Credential={secret_id}/{credential_scope}, SignedHeaders=content-type;host, Signature={signature}"

    resp = httpx.post(
        f"https://{host}",
        headers={
            "Authorization": auth,
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "X-TC-Action": action,
            "X-TC-Version": version,
            "X-TC-Timestamp": str(timestamp),
        },
        content=payload_str,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if "Response" in result and "Result" in result["Response"]:
        return result["Response"]["Result"].strip()
    error = result.get("Response", {}).get("Error", {})
    raise RuntimeError(f"腾讯云ASR错误: {error.get('Code')} {error.get('Message')}")


def transcribe(wav_bytes, cfg):
    import time
    if _is_silent(wav_bytes):
        log.info("[STT] 跳过静音")
        return ""
    t0 = time.perf_counter()
    engine = cfg["stt"]["engine"]
    for attempt in range(2):
        try:
            if engine == "remote":
                text = transcribe_remote(wav_bytes, cfg)
            elif engine == "tencent":
                text = transcribe_tencent(wav_bytes, cfg)
            else:
                text = transcribe_local(wav_bytes, cfg)
            break
        except (ConnectionError, OSError) as e:
            if attempt == 0:
                log.info(f"[STT] 连接失败，重试: {e}")
                continue
            raise
    elapsed = time.perf_counter() - t0
    log.info(f"[STT] ({elapsed:.2f}s) {text}")
    return _fix_punct(_t2s.convert(text))
