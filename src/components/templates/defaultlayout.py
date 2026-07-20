import customtkinter as ctk
from typing import Optional, Callable
from ..organisms import HeaderOrganism, SideMenu
from ..molecules import ModalDialog


class DefaultLayout(ctk.CTkFrame):
    """
    Template: default page layout with a fixed header, collapsible SideMenu, and content area.
    """
    def __init__(
        self,
        parent,
        title: str,
        current_page: str = "DashboardPage",
        on_logout: Optional[Callable] = None,
        on_back: Optional[Callable] = None,
        **kwargs,
    ):
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self._parent_app = parent
        self._current_page = current_page

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Fixed top header ---
        self.header = HeaderOrganism(
            self,
            title=title,
            on_toggle_menu=self._toggle_menu,
            on_notifications=self._show_notifications_modal,
            on_logout=on_logout,
            on_back=on_back,
        )
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew")


        # --- SideMenu navigation ---
        self.sidemenu = SideMenu(
            self,
            on_navigate=self._navigate_to,
            current_page=current_page,
        )
        self.sidemenu.grid(row=1, column=0, sticky="nsew")

        # --- Main content area ---
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_frame.grid(row=1, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

    def _toggle_menu(self) -> None:
        self.sidemenu.toggle_collapse()


    def _navigate_to(self, page_name: str) -> None:
        if hasattr(self._parent_app, "show_page"):
            self._parent_app.show_page(page_name)

    def _show_notifications_modal(self) -> None:
        from use_cases import ProjectManagerUseCase
        manager = ProjectManagerUseCase()
        unreads = manager.get_unread_notifications()

        if not unreads:
            msg = "Você não possui novos alertas de atualizações em seus projetos."
        else:
            msg = "\n\n".join([f"🔔 {n.message} ({n.timestamp})" for n in unreads[:5]])
            manager.mark_all_as_read()

        ModalDialog(
            self._parent_app,
            title="Alertas do Projeto",
            message=msg,
            cancel_label="Fechar",
        )

