import io
import wave
import collections
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
PRE_BUFFER_SEC = 0.5  # 预缓冲秒数

class Recorder:
    def __init__(self):
        self._recording = False
        self._chunks = []
        # 环形缓冲区：保留最近的音频帧
        max_pre_frames = int(SAMPLE_RATE * PRE_BUFFER_SEC / 1024) + 1
        self._ring = collections.deque(maxlen=max_pre_frames)
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            blocksize=1024, callback=self._callback,
        )
        self._stream.start()

    def _callback(self, data, frames, time_info, status):
        chunk = data.copy()
        if self._recording:
            self._chunks.append(chunk)
        else:
            self._ring.append(chunk)

    def start(self):
        self._chunks = list(self._ring)  # 把预缓冲的音频加进来
        self._ring.clear()
        self._recording = True

    def stop(self) -> bytes:
        self._recording = False
        audio = np.concatenate(self._chunks)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())
        return buf.getvalue()
