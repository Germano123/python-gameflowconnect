import customtkinter as ctk
from typing import Optional, Callable

# ------------------------------------------------------------------ #
# Paleta de cores da identidade visual GameFlowConnect
# ------------------------------------------------------------------ #
COLORS = {
    "primary":    "#1e3743",
    "secondary":  "#1e3760",
    "success":    "#00aa00",
    "success_hover": "#008800",
    "danger":     "#c0392b",
    "danger_hover": "#a93226",
    "neutral":    "#4a5568",
    "neutral_hover": "#3a4558",
    "text_light": "#ffffff",
    "text_dark":  "#1e3743",
    "primary_hover":   "#16293a",
    "secondary_hover": "#162850",
}

FONT_SIZES = {
    "small":  10,
    "medium": 13,
    "large":  15,
}

CORNER_RADIUS = {
    "small":  6,
    "medium": 8,
    "large":  10,
}


class ButtonComponent:
    """
    Atom component: a styled button using customtkinter.

    Args:
        parent: The parent widget.
        label (str): Button label text.
        onClick (Callable, optional): Callback invoked on click.
        variant (str): "primary" | "secondary" | "success" | "danger" | "neutral".
        disabled (bool): If True, the button is non-interactive.
        icon (str, optional): Path to an image file to display on the button.
        size (str): "small" | "medium" | "large".
        width (int, optional): Fixed button width in pixels.
    """
    def __init__(
        self,
        parent,
        label: str = "Button",
        onClick: Optional[Callable] = None,
        variant: str = "primary",
        disabled: bool = False,
        icon: Optional[str] = None,
        size: str = "medium",
        width: int = 0,
    ):
        fg    = COLORS.get(variant, COLORS["primary"])
        hover = COLORS.get(f"{variant}_hover", COLORS["primary_hover"])

        kwargs = dict(
            master=parent,
            text=label,
            command=onClick,
            state="disabled" if disabled else "normal",
            fg_color=fg,
            hover_color=hover,
            text_color=COLORS["text_light"],
            corner_radius=CORNER_RADIUS[size],
            font=ctk.CTkFont(family="Arial", size=FONT_SIZES[size], weight="bold"),
        )
        if width:
            kwargs["width"] = width

        self.button = ctk.CTkButton(**kwargs)

    # Geometry manager proxies — keeps the same API as before
    def pack(self, **kwargs):
        self.button.pack(**kwargs)

    def grid(self, **kwargs):
        self.button.grid(**kwargs)

    def place(self, **kwargs):
        self.button.place(**kwargs)

    def configure(self, **kwargs):
        self.button.configure(**kwargs)
