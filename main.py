import queue
import threading
import signal
import sys
import yaml
import time
import pystray
import pyperclip
import pyautogui
from pynput import keyboard
from PIL import Image, ImageDraw
from recorder import Recorder
from stt import transcribe, preload
from llm import polish, preload as preload_llm
from output import type_text

def load_config():
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

SPECIAL_KEYS = {
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "alt_r": keyboard.Key.alt_gr,
    "alt_l": keyboard.Key.alt_l,
    "shift_r": keyboard.Key.shift_r,
    "shift_l": keyboard.Key.shift_l,
}

CFG = load_config()
rec = Recorder()
recording = False
tray_icon = None
task_queue = queue.Queue()


TERMINAL_PROCESSES = ("windowsterminal.exe", "powershell.exe", "cmd.exe", "pwsh.exe",
                      "conhost.exe", "cmder.exe", "mintty.exe", "alacritty.exe", "wezterm-gui.exe")


def _get_foreground_window():
    """获取当前前台窗口的进程名和标题"""
    try:
        import ctypes
        from ctypes import wintypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)  # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.psapi.GetModuleFileNameExW(handle, None, buf, 260)
        ctypes.windll.kernel32.CloseHandle(handle)
        import os
        proc_name = os.path.basename(buf.value).lower()
        # 也获取标题
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        tbuf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, tbuf, length + 1)
        return proc_name, tbuf.value
    except Exception:
        return "", ""


def _is_terminal(proc_name):
    return proc_name in TERMINAL_PROCESSES


def _try_copy_selection(proc_name, title):
    """尝试复制选中文本，返回选中的文本或 None"""
    print(f"[窗口] {proc_name} | {title}")
    if _is_terminal(proc_name):
        return None
    import ctypes
    old_seq = ctypes.windll.user32.GetClipboardSequenceNumber()
    kb = keyboard.Controller()
    kb.press(keyboard.Key.ctrl_l)
    kb.press('c')
    kb.release('c')
    kb.release(keyboard.Key.ctrl_l)
    time.sleep(0.15)
    new_seq = ctypes.windll.user32.GetClipboardSequenceNumber()
    if new_seq != old_seq:
        return pyperclip.paste().strip() or None
    return None


def worker():
    while True:
        item = task_queue.get()
        if item is None:
            break
        wav, selected, is_terminal, mode = item
        try:
            text = transcribe(wav, CFG)
            if text:
                if mode == "bash":
                    text = polish(text, CFG, force_profile="bash")
                else:
                    text = polish(text, CFG, selected_text=selected)
                type_text(text, is_terminal=is_terminal)
        except Exception as e:
            print(f"[错误] {e}")
        task_queue.task_done()


def parse_hotkey(s):
    s = s.strip().lower()
    if s in SPECIAL_KEYS:
        return SPECIAL_KEYS[s]
    return keyboard.KeyCode.from_char(s)


HOTKEY = parse_hotkey(CFG.get("hotkey", "ctrl_r"))
BASH_HOTKEY = keyboard.Key.alt_gr


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


selected_text = None

_current_is_terminal = False
_current_mode = None  # "input" or "bash"

def on_press(key):
    global recording, selected_text, _current_is_terminal, _current_mode
    if recording:
        return
    if key == HOTKEY:
        _current_mode = "input"
    elif key == BASH_HOTKEY:
        _current_mode = "bash"
    else:
        return
    proc_name, title = _get_foreground_window()
    _current_is_terminal = _is_terminal(proc_name)
    if _current_mode == "input":
        selected_text = _try_copy_selection(proc_name, title)
        if selected_text:
            print(f"[选中文本] {selected_text[:50]}...")
    else:
        selected_text = None
    recording = True
    print(f"[录音中...] mode={_current_mode}")
    update_icon(True)
    rec.start()


def on_release(key):
    global recording, selected_text, _current_mode
    if not recording:
        return
    if (_current_mode == "input" and key == HOTKEY) or \
       (_current_mode == "bash" and key == BASH_HOTKEY):
        recording = False
        update_icon(False)
        wav = rec.stop()
        if len(wav) < 16000:
            return
        task_queue.put((wav, selected_text, _current_is_terminal, _current_mode))
        selected_text = None
    qsize = task_queue.qsize()
    if qsize > 1:
        print(f"[队列] {qsize} 条待处理")


def quit_app(icon, _):
    task_queue.put(None)
    icon.stop()


def main():
    global tray_icon
    hotkey = CFG.get("hotkey", "ctrl_r")
    print(f"热键: {hotkey} | STT: {CFG['stt']['engine']}")
    preload(CFG)
    preload_llm(CFG)

    threading.Thread(target=worker, daemon=True).start()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release, daemon=True)
    listener.start()

    tray_icon = pystray.Icon("voice", make_icon(), "语音输入", menu=pystray.Menu(
        pystray.MenuItem("退出", quit_app),
    ))
    print("语音输入已启动")
    signal.signal(signal.SIGINT, lambda *_: quit_app(tray_icon, None))
    tray_icon.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    sys.exit(0)
