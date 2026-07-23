import customtkinter as ctk
import threading
from ..templates import DefaultLayout
from ..atoms import ButtonComponent, TitleText, SubtitleText, BodyText, StatusBadge
from ..molecules import FileCard, ModalDialog


class DashboardPage(DefaultLayout):
    """
    Page: Dashboard principal da aplicação.

    Apresenta uma visão geral dos projetos sincronizados localmente (à esquerda)
    e o feed global de notificações e atualizações de assets da equipe no Drive (à direita).
    """
    def __init__(self, parent):
        self._parent = parent
        super().__init__(
            parent,
            title="Dashboard",
            current_page="DashboardPage",
            on_logout=self._on_logout,
        )
        self._demo_banner_shown = False
        self._build_ui()

    def _build_ui(self) -> None:
        cf = self.content_frame
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_columnconfigure(1, weight=1)
        cf.grid_rowconfigure(2, weight=1)

        # ── Demo mode banner ─────────────────────────────────────────────
        self._demo_banner = ctk.CTkFrame(cf, corner_radius=0, fg_color="#b87900", height=38)
        self._demo_banner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self._demo_banner,
            text="🚀  MODO DEMO",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color="#0f1e26",
        ).grid(row=0, column=0, padx=16, pady=8, sticky="w")

        ctk.CTkLabel(
            self._demo_banner,
            text="Utilizando dados de simulação. Conecte sua conta do Drive em 'Integrações'.",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="#0f1e26",
        ).grid(row=0, column=1, padx=4, pady=8, sticky="w")

        # ── Toolbar ──────────────────────────────────────────────────────
        toolbar = ctk.CTkFrame(cf, corner_radius=8, fg_color="#162c38", height=46)
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 8))
        toolbar.grid_propagate(False)
        toolbar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            toolbar,
            text="🏠  Painel de Controle",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, padx=14, pady=10, sticky="w")

        self._status_lbl = ctk.CTkLabel(
            toolbar,
            text="Pronto",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="#7fa8c0",
        )
        self._status_lbl.grid(row=0, column=1, padx=8, sticky="w")

        ButtonComponent(
            parent=toolbar,
            label="↻  Sincronizar Feed",
            size="small",
            variant="secondary",
            onClick=self._refresh_all,
        ).grid(row=0, column=2, padx=(0, 10), pady=8, sticky="e")

        # ── Projects list panel (Left) ───────────────────────────────────
        self._proj_panel = self._make_panel(cf, "📁 Projetos Sincronizados", row=2, col=0)
        self._projects_scroll = ctk.CTkScrollableFrame(self._proj_panel, fg_color="transparent")
        self._projects_scroll.pack(fill="both", expand=True, padx=6, pady=6)

        # ── Activity Feed panel (Right) ──────────────────────────────────
        self._feed_panel = self._make_panel(cf, "🔔 Atualizações & Atividades Recentes", row=2, col=1)
        self._feed_scroll = ctk.CTkScrollableFrame(self._feed_panel, fg_color="transparent")
        self._feed_scroll.pack(fill="both", expand=True, padx=6, pady=6)

    def on_show(self) -> None:
        from state import AppState
        if AppState.demo_mode:
            self._demo_banner.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
            self._demo_banner_shown = True
        else:
            self._demo_banner.grid_remove()
            self._demo_banner_shown = False

        self._refresh_all()

    def _refresh_all(self) -> None:
        self._status_lbl.configure(text="Sincronizando com o Google Drive...")
        threading.Thread(target=self._load_data_thread, daemon=True).start()

    def _load_data_thread(self) -> None:
        from use_cases import ProjectManagerUseCase
        from state import AppState

        manager = ProjectManagerUseCase()
        
        # 1. Carregar lista de projetos do SQLite
        projects = manager.list_projects()
        
        # 2. Obter notificações do log no Drive
        notifications = []
        if AppState.is_drive_connected():
            try:
                notifications = manager.get_unread_notifications(AppState.drive_service, projects)
            except Exception as e:
                print(f"Erro ao buscar notificações do Drive: {e}")

        # Renderizar na UI na thread do Tkinter
        self.after(0, lambda: self._render_ui(projects, notifications))

    def _render_ui(self, projects, notifications) -> None:
        self._status_lbl.configure(text="Sincronizado")
        
        # Renderizar Projetos
        for w in self._projects_scroll.winfo_children():
            w.destroy()

        if not projects:
            ctk.CTkLabel(
                self._projects_scroll,
                text="Nenhum projeto sincronizado localmente.\nVá para a página 'Projetos' para criar ou importar.",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color="gray50",
            ).pack(pady=40)
        else:
            for proj in projects:
                card = ctk.CTkFrame(self._projects_scroll, corner_radius=8, fg_color="#1a3040", border_width=1, border_color="#2d4a5a")
                card.pack(fill="x", padx=4, pady=4)
                
                ctk.CTkLabel(
                    card,
                    text=f"📁 {proj.name}",
                    font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
                    text_color="#ffffff",
                    anchor="w"
                ).pack(fill="x", padx=12, pady=(8, 2))

                ctk.CTkLabel(
                    card,
                    text=f"Diretório: {proj.local_path}\nProprietário: {proj.owner}",
                    font=ctk.CTkFont(family="Arial", size=10),
                    text_color="gray60",
                    anchor="w",
                    justify="left"
                ).pack(fill="x", padx=12, pady=(0, 8))

        # Renderizar Feed de Atividades
        for w in self._feed_scroll.winfo_children():
            w.destroy()

        if not notifications:
            ctk.CTkLabel(
                self._feed_scroll,
                text="Sem novas atualizações de assets no momento.",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color="gray50",
            ).pack(pady=40)
        else:
            for notif in notifications:
                card = ctk.CTkFrame(self._feed_scroll, corner_radius=8, fg_color="#1e3743", border_width=1, border_color="#00aa00")
                card.pack(fill="x", padx=4, pady=4)

                ctk.CTkLabel(
                    card,
                    text=notif.message,
                    font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
                    text_color="#ffffff",
                    anchor="w",
                    justify="left"
                ).pack(fill="x", padx=12, pady=(8, 2))

                ctk.CTkLabel(
                    card,
                    text=f"Enviado em: {notif.timestamp} por {notif.author}",
                    font=ctk.CTkFont(family="Arial", size=10),
                    text_color="#00ff00",
                    anchor="w"
                ).pack(fill="x", padx=12, pady=(0, 8))

    def _make_panel(self, parent, title: str, row: int, col: int) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(parent, corner_radius=10, border_width=1, border_color="#2d4a5a")
        outer.grid(
            row=row, column=col, sticky="nsew",
            padx=(14 if col == 0 else 7, 7 if col == 0 else 14),
            pady=(0, 14),
        )
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(outer, corner_radius=0, fg_color="#1e3743", height=40)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(
            hdr,
            text=title,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color="#ffffff",
        ).pack(side="left", padx=14, pady=10)

        content = ctk.CTkFrame(outer, corner_radius=0, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        return content

    def _on_logout(self) -> None:
        from state import AppState
        AppState.clear()
        self._demo_banner.grid_remove()
        self._demo_banner_shown = False
        self._parent.show_page("HomePage")
