import customtkinter as ctk
from typing import Callable, Optional


class SideMenu(ctk.CTkFrame):
    """
    Organism Component: Side Navigation Menu.

    Provides navigation between Dashboard, Projetos, Integrações, Configurações, and Perfil.
    Can be expanded or collapsed via the Hamburger button toggle.
    """
    ACCENT_COLOR = "#00aa00"
    ACTIVE_BG    = "#1e3760"
    HOVER_BG     = "#162c38"
    BG_COLOR     = "#13232c"

    _ITEMS = [
        ("Dashboard",     "📊  Dashboard",     "DashboardPage"),
        ("Workspaces",    "📁  Workspaces",    "WorkspacesPage"),
        ("Integrações",   "🔗  Integrações",   "IntegrationsPage"),
        ("Configurações", "⚙️  Configurações", "SettingsPage"),
        ("Perfil",        "👤  Perfil",        "ProfilePage"),
    ]


    def __init__(self, parent, on_navigate: Callable[[str], None], current_page: str = "DashboardPage", **kwargs):
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", self.BG_COLOR)
        kwargs.setdefault("width", 210)
        super().__init__(parent, **kwargs)

        self._on_navigate = on_navigate
        self._current_page = current_page
        self._collapsed = False
        self._buttons: dict[str, ctk.CTkButton] = {}

        self.grid_rowconfigure(len(self._ITEMS) + 1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self) -> None:
        # Title section inside SideMenu
        title_lbl = ctk.CTkLabel(
            self,
            text="NAVEGAÇÃO",
            font=ctk.CTkFont(family="Arial", size=10, weight="bold"),
            text_color="gray50",
            anchor="w",
        )
        title_lbl.grid(row=0, column=0, padx=16, pady=(16, 10), sticky="ew")

        # Navigation items
        for idx, (short_name, label, page_name) in enumerate(self._ITEMS, start=1):
            is_active = (page_name == self._current_page)
            btn = ctk.CTkButton(
                self,
                text=label,
                font=ctk.CTkFont(family="Arial", size=12, weight="bold" if is_active else "normal"),
                fg_color=self.ACTIVE_BG if is_active else "transparent",
                hover_color=self.HOVER_BG,
                text_color="#ffffff" if is_active else "#a0b8c8",
                anchor="w",
                height=40,
                corner_radius=8,
                command=lambda p=page_name: self._handle_click(p),
            )
            btn.grid(row=idx, column=0, padx=8, pady=3, sticky="ew")
            self._buttons[page_name] = btn

    def _handle_click(self, page_name: str) -> None:
        self.set_active(page_name)
        if self._on_navigate:
            self._on_navigate(page_name)

    def set_active(self, page_name: str) -> None:
        self._current_page = page_name
        for p_name, btn in self._buttons.items():
            is_active = (p_name == page_name)
            btn.configure(
                fg_color=self.ACTIVE_BG if is_active else "transparent",
                text_color="#ffffff" if is_active else "#a0b8c8",
                font=ctk.CTkFont(family="Arial", size=12, weight="bold" if is_active else "normal"),
            )

    def toggle_collapse(self) -> bool:
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.grid_remove()
        else:
            self.grid()
        return self._collapsed
