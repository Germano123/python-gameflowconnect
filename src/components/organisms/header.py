import customtkinter as ctk
from typing import Optional, Callable
from ..atoms import ButtonComponent


class HeaderOrganism(ctk.CTkFrame):
    """
    Organism component: top navigation bar.

    Args:
        parent: The parent widget.
        title (str): Page title displayed in the center/left of the header.
        on_back (Callable, optional): If provided, shows a Back button on the left.
        on_logout (Callable, optional): If provided, shows a Logout button on the right.
        **kwargs: Additional keyword arguments forwarded to ctk.CTkFrame.
    """
    HEIGHT = 56

    def __init__(
        self,
        parent,
        title: str,
        on_back: Optional[Callable] = None,
        on_logout: Optional[Callable] = None,
        **kwargs,
    ):
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", "#1e3743")
        kwargs.setdefault("height", self.HEIGHT)
        super().__init__(parent, **kwargs)

        self.pack_propagate(False)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)  # title expands

        col = 0

        # --- Back button (optional) ---
        if on_back:
            ButtonComponent(
                parent=self,
                label="← Voltar",
                size="small",
                variant="secondary",
                onClick=on_back,
            ).grid(row=0, column=col, padx=(12, 4), pady=10, sticky="w")
            col += 1

        # --- App logo / page title ---
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.grid(row=0, column=col, sticky="w", padx=14, pady=8)

        ctk.CTkLabel(
            logo_frame,
            text="⬡",
            font=ctk.CTkFont(size=18),
            text_color="#00aa00",
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            logo_frame,
            text=title,
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            text_color="#ffffff",
        ).pack(side="left")

        # --- Right actions ---
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="e", padx=12, pady=8)

        if on_logout:
            ButtonComponent(
                parent=right_frame,
                label="Sair",
                size="small",
                variant="danger",
                onClick=on_logout,
            ).pack(side="right")
