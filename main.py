import queue
import threading
import signal
import sys
import os
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
recording = False
tray_icon = None
task_queue = queue.Queue()

# 当前录音会话的上下文（按下热键时确定，整个会话共享）
_current_selected = None
_current_is_terminal = False
_current_mode = None
_current_window_title = ""  # 按下时记录，供 LLM profile 匹配
_segment_count = 0  # 当前会话已切割的段数


def _on_segment(wav):
    """录音中静音切割回调"""
    global _segment_count
    _segment_count += 1
    print(f"[自动切割] 第{_segment_count}段 {len(wav)} bytes")
    # 只有第一段用 selected_text，后续段不走 command 模式
    selected = _current_selected if _segment_count == 1 else None
    task_queue.put((wav, selected, _current_is_terminal, _current_mode, _current_window_title))


rec = Recorder(on_segment=_on_segment)


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
        handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.psapi.GetModuleFileNameExW(handle, None, buf, 260)
        ctypes.windll.kernel32.CloseHandle(handle)
        proc_name = os.path.basename(buf.value).lower()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        tbuf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, tbuf, length + 1)
        return proc_name, tbuf.value
    except Exception:
        return "", ""


def _is_terminal(proc_name):
    return proc_name in TERMINAL_PROCESSES


def _try_copy_selection(proc_name):
    """尝试复制选中文本，返回选中的文本或 None"""
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
        wav, selected, is_terminal, mode, window_title = item
        try:
            update_icon("processing")
            text = transcribe(wav, CFG)
            if text:
                if mode == "bash":
                    text = polish(text, CFG, force_profile="bash")
                elif selected:
                    text = polish(text, CFG, selected_text=selected)
                else:
                    text = polish(text, CFG, window_title=window_title)
                type_text(text, is_terminal=is_terminal)
        except Exception as e:
            print(f"[错误] {e}")
        finally:
            if not recording:
                update_icon("idle")
        task_queue.task_done()


def parse_hotkey(s):
    s = s.strip().lower()
    if s in SPECIAL_KEYS:
        return SPECIAL_KEYS[s]
    return keyboard.KeyCode.from_char(s)


HOTKEY = parse_hotkey(CFG.get("hotkey", "ctrl_r"))
BASH_HOTKEY = keyboard.Key.alt_gr


def make_icon(state="idle"):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if state == "recording":
        fill, accent = (220, 80, 80), (230, 100, 100)
    elif state == "processing":
        fill, accent = (220, 180, 50), (230, 200, 70)
    else:
        fill, accent = (60, 160, 80), (80, 180, 100)
    d.rounded_rectangle([22, 8, 42, 34], radius=10, fill=fill)
    d.arc([14, 18, 50, 48], start=0, end=180, fill=accent, width=3)
    d.line([32, 48, 32, 56], fill=accent, width=3)
    d.line([24, 56, 40, 56], fill=accent, width=3)
    return img


def update_icon(state="idle"):
    if tray_icon:
        tray_icon.icon = make_icon(state)


def on_press(key):
    global recording, _current_selected, _current_is_terminal, _current_mode, _current_window_title, _segment_count
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
    _current_window_title = title
    _segment_count = 0
    print(f"[窗口] {proc_name} | {title}")
    if _current_mode == "input":
        _current_selected = _try_copy_selection(proc_name)
        if _current_selected:
            print(f"[选中文本] {_current_selected[:50]}...")
    else:
        _current_selected = None
    recording = True
    print(f"[录音中...] mode={_current_mode}")
    update_icon("recording")
    rec.start()


def on_release(key):
    global recording
    if not recording:
        return
    if (_current_mode == "input" and key == HOTKEY) or \
       (_current_mode == "bash" and key == BASH_HOTKEY):
        recording = False
        update_icon("idle")
        wav = rec.stop()
        if len(wav) < 16000:
            return
        # 最后一段：如果之前有切割过，selected 设为 None
        selected = _current_selected if _segment_count == 0 else None
        task_queue.put((wav, selected, _current_is_terminal, _current_mode, _current_window_title))
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
