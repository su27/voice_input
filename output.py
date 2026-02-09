import pyperclip
import pyautogui

def type_text(text: str):
    """通过剪贴板+粘贴输出文本到当前光标位置"""
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")
