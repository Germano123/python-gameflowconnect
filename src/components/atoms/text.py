import tkinter as tk

def TextComponent(content: str, font: str = ("Arial", 14), **kwargs) -> tk.Label:
    return tk.Label(text=content, font=font, **kwargs)
