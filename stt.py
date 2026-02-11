import io
import wave
import httpx
import opencc
import numpy as np
from faster_whisper import WhisperModel

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


def _get_model(cfg):
    global _model
    if _model is None:
        local = cfg["stt"]["local"]
        print(f"[STT] 加载 {local['model']}...")
        _model = WhisperModel(local["model"], device=local["device"], compute_type="auto")
        print("[STT] 就绪")
    return _model


def preload(cfg):
    if cfg["stt"]["engine"] == "local":
        _get_model(cfg)
    print(f"[STT] engine={cfg['stt']['engine']}")


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


def transcribe(wav_bytes, cfg):
    import time
    if _is_silent(wav_bytes):
        print("[STT] 跳过静音")
        return ""
    t0 = time.perf_counter()
    if cfg["stt"]["engine"] == "remote":
        text = transcribe_remote(wav_bytes, cfg)
    else:
        text = transcribe_local(wav_bytes, cfg)
    elapsed = time.perf_counter() - t0
    print(f"[STT] ({elapsed:.2f}s) {text}")
    return _fix_punct(_t2s.convert(text))
