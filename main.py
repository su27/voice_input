import threading
import sys
import yaml
import pystray
from pynput import keyboard
from PIL import Image, ImageDraw
from recorder import Recorder
from stt import transcribe, preload, unload
from llm import polish, preload as preload_llm
from output import type_text

def load_config():
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

SPECIAL_KEYS = {
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "shift_r": keyboard.Key.shift_r,
    "shift_l": keyboard.Key.shift_l,
}

CFG = load_config()
rec = Recorder()
recording = False
tray_icon = None


def parse_hotkey(s):
    s = s.strip().lower()
    if s in SPECIAL_KEYS:
        return SPECIAL_KEYS[s]
    return keyboard.KeyCode.from_char(s)


HOTKEY = parse_hotkey(CFG.get("hotkey", "ctrl_r"))


def is_hotkey(key):
    return key == HOTKEY


def make_icon(active=False):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if active:
        fill, accent = (220, 80, 80), (230, 100, 100)
    else:
        fill, accent = (60, 160, 80), (80, 180, 100)
    d.rounded_rectangle([22, 8, 42, 34], radius=10, fill=fill)
    d.arc([14, 18, 50, 48], start=0, end=180, fill=accent, width=3)
    d.line([32, 48, 32, 56], fill=accent, width=3)
    d.line([24, 56, 40, 56], fill=accent, width=3)
    return img


def update_icon(active=False):
    if tray_icon:
        tray_icon.icon = make_icon(active)


def on_press(key):
    global recording
    if is_hotkey(key) and not recording:
        recording = True
        print("[录音中...]")
        update_icon(True)
        rec.start()


def on_release(key):
    global recording
    if is_hotkey(key) and recording:
        recording = False
        update_icon(False)
        wav = rec.stop()
        threading.Thread(target=process, args=(wav,), daemon=True).start()


def process(wav: bytes):
    try:
        text = transcribe(wav, CFG)
        print(f"[识别] {text}")
        if text:
            text = polish(text, CFG)
            print(f"[输出] {text}")
            type_text(text)
    except Exception as e:
        print(f"[错误] {e}")


def toggle_model(icon, _):
    import stt
    if stt._model is not None:
        unload()
        print("[模型已卸载]")
    else:
        preload(CFG)


def quit_app(icon, _):
    icon.stop()


def main():
    global tray_icon
    hotkey = CFG.get("hotkey", "ctrl_r")
    print(f"热键: {hotkey} | STT: {CFG['stt']['engine']}")
    preload(CFG)
    preload_llm(CFG)

    listener = keyboard.Listener(on_press=on_press, on_release=on_release, daemon=True)
    listener.start()

    tray_icon = pystray.Icon("voice", make_icon(), "语音输入", menu=pystray.Menu(
        pystray.MenuItem("退出", quit_app),
    ))
    print(f"语音输入已启动，按住 {hotkey} 录音")
    tray_icon.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    sys.exit(0)
