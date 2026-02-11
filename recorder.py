import io
import wave
import collections
import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
PRE_BUFFER_SEC = 0.5
BLOCK_SIZE = 1024

MIN_DURATION_SEC = 6
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION_SEC = 0.8


def _to_wav(audio_data):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


class Recorder:
    def __init__(self, on_segment=None):
        self._recording = False
        self._chunks = []
        self._on_segment = on_segment
        self._silence_frames = 0
        self._total_frames = 0
        self._silence_limit = int(SILENCE_DURATION_SEC * SAMPLE_RATE / BLOCK_SIZE)
        self._min_frames = int(MIN_DURATION_SEC * SAMPLE_RATE / BLOCK_SIZE)

        max_pre_frames = int(SAMPLE_RATE * PRE_BUFFER_SEC / BLOCK_SIZE) + 1
        self._ring = collections.deque(maxlen=max_pre_frames)
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            blocksize=BLOCK_SIZE, callback=self._callback,
        )
        self._stream.start()

    def _callback(self, data, frames, time_info, status):
        chunk = data.copy()
        if self._recording:
            self._chunks.append(chunk)
            self._total_frames += 1
            rms = np.sqrt(np.mean(chunk ** 2))
            if rms < SILENCE_THRESHOLD:
                self._silence_frames += 1
            else:
                self._silence_frames = 0
            if (self._total_frames > self._min_frames and
                    self._silence_frames >= self._silence_limit and
                    self._on_segment):
                # 把 chunks 取走，WAV 编码放到别的线程避免阻塞音频回调
                chunks = self._chunks
                self._chunks = []
                self._total_frames = 0
                self._silence_frames = 0
                threading.Thread(target=self._emit_segment, args=(chunks,), daemon=True).start()
        else:
            self._ring.append(chunk)

    def _emit_segment(self, chunks):
        audio = np.concatenate(chunks)
        wav = _to_wav(audio)
        self._on_segment(wav)

    def start(self):
        self._chunks = list(self._ring)
        self._ring.clear()
        self._total_frames = len(self._chunks)
        self._silence_frames = 0
        self._recording = True

    def stop(self):
        self._recording = False
        if not self._chunks:
            return b""
        audio = np.concatenate(self._chunks)
        return _to_wav(audio)
