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


class TitleText(TextComponent):
    """Convenience atom for section/page titles."""
    def __init__(self, parent, text: str, **kwargs):
        kwargs.setdefault("font", ("Arial", 16, "bold"))
        kwargs.setdefault("text_color", "#ffffff")
        super().__init__(parent, content=text, **kwargs)


class SubtitleText(TextComponent):
    """Convenience atom for subtitles and secondary headers."""
    def __init__(self, parent, text: str, **kwargs):
        kwargs.setdefault("font", ("Arial", 12))
        kwargs.setdefault("text_color", "gray60")
        super().__init__(parent, content=text, **kwargs)


class BodyText(TextComponent):
    """Convenience atom for regular body text."""
    def __init__(self, parent, text: str, **kwargs):
        kwargs.setdefault("font", ("Arial", 11))
        kwargs.setdefault("text_color", "#a0b8c8")
        super().__init__(parent, content=text, **kwargs)


class CaptionText(TextComponent):
    """Convenience atom for small captions."""
    def __init__(self, parent, text: str, **kwargs):
        kwargs.setdefault("font", ("Arial", 10))
        kwargs.setdefault("text_color", "gray50")
        super().__init__(parent, content=text, **kwargs)


class StatusBadge(ctk.CTkFrame):
    """Atom component: pill badge for status indicators."""
    def __init__(self, parent, text: str, bg_color: str = "#1e3743", text_color: str = "#00aa00", **kwargs):
        kwargs.setdefault("corner_radius", 6)
        kwargs.setdefault("fg_color", bg_color)
        super().__init__(parent, **kwargs)
        ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
            text_color=text_color,
        ).pack(padx=8, pady=2)
