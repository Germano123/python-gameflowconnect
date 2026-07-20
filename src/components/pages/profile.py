import customtkinter as ctk
from ..templates import DefaultLayout
from ..atoms import TitleText, SubtitleText


class ProfilePage(DefaultLayout):
    """
    Page: Perfil.
    Layout limpo e estruturado para gerenciamento de perfil e conta de usuário.
    """
    def __init__(self, parent):
        self._parent = parent
        super().__init__(
            parent,
            title="Perfil",
            current_page="ProfilePage",
            on_logout=self._on_logout,
        )
        self._build_ui()

    def _build_ui(self) -> None:
        cf = self.content_frame
        center = ctk.CTkFrame(cf, corner_radius=12, border_width=1, border_color="#2d4a5a", fg_color="#162c38", width=500, height=250)
        center.place(relx=0.5, rely=0.4, anchor="center")
        center.grid_propagate(False)

        TitleText(center, text="👤  Perfil do Usuário").pack(pady=(36, 8))
        SubtitleText(center, text="Você está na página Perfil.").pack(pady=4)

    def _on_logout(self) -> None:
        from state import AppState
        AppState.clear()
        self._parent.show_page("HomePage")
