import customtkinter as ctk


class TextComponent(ctk.CTkLabel):
    """
    Atom component: a styled label using customtkinter.

    Args:
        parent: The parent widget.
        content (str): Text to display.
        font (tuple, optional): (family, size) or (family, size, weight). Defaults to ("Arial", 14).
        **kwargs: Additional keyword arguments forwarded to ctk.CTkLabel.
    """
    def __init__(self, parent, content: str, font: tuple = ("Arial", 14), **kwargs):
        # Convert tuple font spec to CTkFont
        if isinstance(font, tuple):
            family = font[0] if len(font) > 0 else "Arial"
            size   = font[1] if len(font) > 1 else 14
            weight = font[2] if len(font) > 2 else "normal"
            ctk_font = ctk.CTkFont(family=family, size=size, weight=weight)
        else:
            ctk_font = font

        # CTkLabel doesn't use 'bg' — map it to fg_color if passed
        if "bg" in kwargs:
            kwargs.setdefault("fg_color", kwargs.pop("bg"))
        if "fg" in kwargs:
            kwargs.setdefault("text_color", kwargs.pop("fg"))

        super().__init__(parent, text=content, font=ctk_font, **kwargs)
