import customtkinter as ctk
from typing import Optional, Callable
from ..atoms import ButtonComponent


class HeaderOrganism(ctk.CTkFrame):
    """
    Organism component: top navigation bar with Hamburger menu button & Notification bell.

    Args:
        parent: The parent widget.
        title (str): Page title displayed in the header.
        on_toggle_menu (Callable, optional): Callback to expand/collapse the SideMenu.
        on_notifications (Callable, optional): Callback to display project update notifications.
        on_logout (Callable, optional): If provided, shows a Logout button on the right.
        **kwargs: Additional keyword arguments forwarded to ctk.CTkFrame.
    """
    HEIGHT = 56

    def __init__(
        self,
        parent,
        title: str,
        on_toggle_menu: Optional[Callable] = None,
        on_notifications: Optional[Callable] = None,
        on_logout: Optional[Callable] = None,
        on_back: Optional[Callable] = None,
        **kwargs,
    ):
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", "#1e3743")
        kwargs.setdefault("height", self.HEIGHT)
        super().__init__(parent, **kwargs)

        self.pack_propagate(False)
        self.grid_propagate(False)
        self.grid_columnconfigure(2, weight=1)  # title frame expands

        col = 0

        # --- Optional Back Button ---
        if on_back:
            ButtonComponent(
                parent=self,
                label="← Voltar",
                size="small",
                variant="secondary",
                onClick=on_back,
            ).grid(row=0, column=col, padx=(10, 4), pady=8, sticky="w")
            col += 1

        # --- Hamburger button (toggle SideMenu) ---
        if on_toggle_menu:
            hamb_btn = ctk.CTkButton(
                self,
                text="☰",
                font=ctk.CTkFont(size=18, weight="bold"),
                fg_color="transparent",
                hover_color="#162c38",
                text_color="#00aa00",
                width=38,
                height=36,
                command=on_toggle_menu,
            )
            hamb_btn.grid(row=0, column=col, padx=(6, 2), pady=8, sticky="w")
            col += 1


        # --- App logo / page title ---
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.grid(row=0, column=col, sticky="w", padx=10, pady=8)

        ctk.CTkLabel(
            logo_frame,
            text="⬡ GameFlow Connect",
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            text_color="#ffffff",
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            logo_frame,
            text=f"│  {title}",
            font=ctk.CTkFont(family="Arial", size=13),
            text_color="#7fa8c0",
        ).pack(side="left")

        # --- Right actions (Notifications & Logout) ---
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.grid(row=0, column=3, sticky="e", padx=12, pady=8)

        if on_notifications:
            notif_btn = ctk.CTkButton(
                right_frame,
                text="🔔  Alertas",
                font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                fg_color="#162c38",
                hover_color="#2d5266",
                text_color="#f0c040",
                height=32,
                width=85,
                command=on_notifications,
            )
            notif_btn.pack(side="left", padx=(0, 8))

        if on_logout:
            ButtonComponent(
                parent=right_frame,
                label="Sair",
                size="small",
                variant="danger",
                onClick=on_logout,
            ).pack(side="left")

