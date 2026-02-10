import time
import pyperclip
import pyautogui


def type_text(text: str):
    """通过剪贴板+粘贴输出文本到当前光标位置，完成后恢复剪贴板"""
    old = pyperclip.paste()
    pyperclip.copy(text)
    pyautogui.hotkey("shift", "insert")
    time.sleep(0.1)
    pyperclip.copy(old)
