import customtkinter as ctk
import threading
from ..templates import DefaultLayout
from ..atoms import ButtonComponent
from ..molecules import FileCard, ModalDialog


class DashboardPage(DefaultLayout):
    """
    Page: main application dashboard.

    Two-column layout: Google Drive files (left) | GitHub repos (right).
    Uses CTkScrollableFrame for native scrolling.

    In demo mode (AppState.demo_mode is True), displays a prominent banner
    and loads data from MockDriveService / MockGitService instead of real APIs.
    Upload is disabled in demo mode.
    """
    ACCENT  = "#00aa00"
    PRIMARY = "#1e3743"

    def __init__(self, parent):
        self._parent = parent
        super().__init__(
            parent,
            title="Dashboard",
            on_logout=self._on_logout,
        )
        self._demo_banner_shown = False
        self._build_ui()

    def _build_ui(self) -> None:
        cf = self.content_frame
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_columnconfigure(1, weight=1)
        cf.grid_rowconfigure(2, weight=1)  # row 0 = demo banner, row 1 = toolbar, row 2 = panels

        # ── Demo mode banner (shown dynamically) ─────────────────────────
        self._demo_banner = ctk.CTkFrame(
            cf,
            corner_radius=0,
            fg_color="#b87900",
            height=38,
        )
        self._demo_banner.grid_columnconfigure(1, weight=1)
        # hidden initially; shown when demo_mode is active

        ctk.CTkLabel(
            self._demo_banner,
            text="🚀  MODO DEMO",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color="#0f1e26",
        ).grid(row=0, column=0, padx=16, pady=8, sticky="w")

        ctk.CTkLabel(
            self._demo_banner,
            text="Você está visualizando dados de exemplo. Nenhuma conta real está conectada.",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="#0f1e26",
        ).grid(row=0, column=1, padx=4, pady=8, sticky="w")

        ctk.CTkButton(
            self._demo_banner,
            text="Criar conta →",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            fg_color="#0f1e26",
            hover_color="#1e3743",
            text_color="#f0c040",
            corner_radius=6,
            width=120,
            height=26,
            command=lambda: self._exit_demo_to_register(),
        ).grid(row=0, column=2, padx=(4, 16), pady=6, sticky="e")

        # ── Status / toolbar ────────────────────────────────────────────
        toolbar = ctk.CTkFrame(cf, corner_radius=8, fg_color="#162c38", height=46)
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 8))
        toolbar.grid_propagate(False)
        toolbar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            toolbar,
            text="⬡  GameFlow Connect",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, padx=14, pady=10, sticky="w")

        self._status_lbl = ctk.CTkLabel(
            toolbar,
            text="Carregando...",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="#7fa8c0",
        )
        self._status_lbl.grid(row=0, column=1, padx=8, sticky="w")

        ButtonComponent(
            parent=toolbar,
            label="↻  Atualizar",
            size="small",
            variant="secondary",
            onClick=self._refresh_all,
        ).grid(row=0, column=2, padx=(0, 10), pady=8, sticky="e")

        # ── Google Drive panel ──────────────────────────────────────────
        drive_panel = self._make_panel(cf, "☁  Google Drive", row=2, col=0)

        upload_row = ctk.CTkFrame(drive_panel, fg_color="transparent")
        upload_row.pack(fill="x", padx=8, pady=(8, 4))

        self._upload_btn = ButtonComponent(
            parent=upload_row,
            label="⬆  Upload de arquivo",
            size="small",
            variant="success",
            onClick=self._upload_file,
        )
        self._upload_btn.pack(side="left")

        self._drive_scroll = ctk.CTkScrollableFrame(
            drive_panel, corner_radius=0, fg_color="transparent", label_text=""
        )
        self._drive_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # ── GitHub panel ────────────────────────────────────────────────
        git_panel = self._make_panel(cf, "🐙  GitHub Repositories", row=2, col=1)

        self._git_scroll = ctk.CTkScrollableFrame(
            git_panel, corner_radius=0, fg_color="transparent", label_text=""
        )
        self._git_scroll.pack(fill="both", expand=True, padx=4, pady=(12, 4))

        # Data loading kicked off by the router lifecycle hook (on_show)

    def on_show(self) -> None:
        """Called when the page is shown. Configures demo banner and loads data."""
        from state import AppState

        if AppState.demo_mode and not self._demo_banner_shown:
            # Show the amber demo banner above the toolbar
            self._demo_banner.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
            self._demo_banner_shown = True
            # Disable upload button in demo mode
            self._upload_btn.configure(state="disabled")
        elif not AppState.demo_mode:
            self._demo_banner.grid_remove()
            self._demo_banner_shown = False
            self._upload_btn.configure(state="normal")

        self._refresh_all()

    # ------------------------------------------------------------------ #
    # Panel factory
    # ------------------------------------------------------------------ #

    def _make_panel(self, parent, title: str, row: int, col: int) -> ctk.CTkFrame:
        """Creates a titled card panel with a dark header."""
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

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #

    def _refresh_all(self) -> None:
        self._status_lbl.configure(text="Atualizando dados...")
        threading.Thread(target=self._load_drive, daemon=True).start()
        threading.Thread(target=self._load_github, daemon=True).start()

    def _load_drive(self) -> None:
        from state import AppState
        from use_cases import ListAssetsUseCase
        from domain import AssetType

        if not AppState.is_drive_connected():
            self.after(0, lambda: self._render_empty(self._drive_scroll, "Drive não conectado.\nFaça login para conectar."))
            return
        try:
            storage_repo = AppState.get_storage_repository()
            local_repo = AppState.get_local_repository()
            list_use_case = ListAssetsUseCase(remote_repo=storage_repo, local_repo=local_repo)
            
            # Sincronização e exibição focada inicialmente em Imagens (Fase 1)
            assets = list_use_case.execute(asset_type=AssetType.IMAGE)
            self.after(0, lambda: self._render_drive(assets))
        except Exception as e:
            self.after(0, lambda: self._render_empty(self._drive_scroll, f"Erro: {e}"))

    def _load_github(self) -> None:
        from state import AppState
        if not AppState.is_github_connected():
            self.after(0, lambda: self._render_empty(self._git_scroll, "GitHub não conectado.\nFaça login para conectar."))
            return
        try:
            repos = AppState.git_service.get_repos()
            username = repos[0].owner.login if repos else "—"
            self.after(0, lambda: self._render_github(repos))
            if AppState.demo_mode:
                self.after(0, lambda: self._status_lbl.configure(
                    text="🚀 Demo — dados de exemplo · 8 repositórios simulados"
                ))
            else:
                self.after(0, lambda: self._status_lbl.configure(text=f"Conectado como @{username}"))
        except Exception as e:
            self.after(0, lambda: self._render_empty(self._git_scroll, f"Erro: {e}"))

    # ------------------------------------------------------------------ #
    # Renderers
    # ------------------------------------------------------------------ #

    def _render_drive(self, assets: list) -> None:
        self._clear(self._drive_scroll)
        if not assets:
            self._render_empty(self._drive_scroll, "Nenhum asset de imagem encontrado.")
            return
        for asset in assets:
            card = FileCard(
                self._drive_scroll,
                name=asset.name,
                mime_type=asset.mime_type or "image/png",
                size=asset.formatted_size,
                modified=(asset.modified_time or "")[:10],
                status_text=asset.status.name if hasattr(asset.status, 'name') else str(asset.status),
                on_sync=lambda a=asset: self._sync_asset(a),
            )
            card.pack(fill="x", padx=4, pady=3)

    def _sync_asset(self, asset) -> None:
        from state import AppState
        from use_cases import SyncAssetUseCase

        self._status_lbl.configure(text=f"Sincronizando {asset.name}...")

        def run():
            try:
                storage_repo = AppState.get_storage_repository()
                local_repo = AppState.get_local_repository()
                sync_use_case = SyncAssetUseCase(remote_repo=storage_repo, local_repo=local_repo)
                saved_path = sync_use_case.download_to_engine(asset)

                self.after(0, lambda: self._status_lbl.configure(
                    text=f"✓ Sincronizado: {asset.name} em {saved_path}"
                ))
                self.after(800, self._refresh_all)
            except Exception as e:
                self.after(0, lambda: self._status_lbl.configure(text=f"Erro sync: {e}"))

        threading.Thread(target=run, daemon=True).start()


    def _render_github(self, repos: list) -> None:
        self._clear(self._git_scroll)
        if not repos:
            self._render_empty(self._git_scroll, "Nenhum repositório encontrado.")
            return
        for repo in repos[:20]:
            row_f = ctk.CTkFrame(
                self._git_scroll,
                corner_radius=8,
                border_width=1,
                border_color="#2d4a5a",
                fg_color="#1a3040",
            )
            row_f.pack(fill="x", padx=4, pady=3)
            row_f.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row_f,
                text=f"🗂  {repo.name}",
                font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
                text_color="#ffffff",
                anchor="w",
            ).grid(row=0, column=0, padx=12, pady=(8, 2), sticky="ew")

            meta_parts = []
            if repo.language:
                meta_parts.append(f"● {repo.language}")
            if repo.stargazers_count:
                meta_parts.append(f"★ {repo.stargazers_count}")
            meta_parts.append("🔒 Private" if repo.private else "🌐 Public")

            ctk.CTkLabel(
                row_f,
                text="  ·  ".join(meta_parts) if meta_parts else "—",
                font=ctk.CTkFont(family="Arial", size=10),
                text_color="gray60",
                anchor="w",
            ).grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")

    def _render_empty(self, frame, message: str) -> None:
        self._clear(frame)
        ctk.CTkLabel(
            frame,
            text=message,
            font=ctk.CTkFont(family="Arial", size=12),
            text_color="gray50",
            justify="center",
        ).pack(pady=36)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def _upload_file(self) -> None:
        from tkinter import filedialog
        from state import AppState

        if AppState.demo_mode:
            # Should not reach here (button is disabled), but guard anyway
            return

        if not AppState.is_drive_connected():
            ModalDialog(
                self._parent,
                title="Drive não conectado",
                message="Conecte sua conta Google Drive na página de Login antes de fazer upload.",
                cancel_label="Fechar",
            )
            return

        path = filedialog.askopenfilename(title="Selecionar arquivo para upload")
        if not path:
            return

        name = path.replace("\\", "/").split("/")[-1]
        ModalDialog(
            self._parent,
            title="Confirmar Upload",
            message=f"Enviar '{name}' para o Google Drive?",
            on_confirm=lambda: self._do_upload(path),
            confirm_label="Upload",
        )

    def _do_upload(self, path: str) -> None:
        from state import AppState
        self._status_lbl.configure(text="Fazendo upload...")

        def run():
            try:
                fid = AppState.drive_service.upload_file(path)
                self.after(0, lambda: self._status_lbl.configure(text=f"Upload OK — ID: {fid}"))
                self.after(800, self._refresh_all)
            except Exception as e:
                self.after(0, lambda: self._status_lbl.configure(text=f"Erro upload: {e}"))

        threading.Thread(target=run, daemon=True).start()

    def _on_logout(self) -> None:
        from state import AppState
        if AppState.demo_mode:
            ModalDialog(
                self._parent,
                title="Sair do Modo Demo",
                message="Deseja sair do modo demo? Você voltará à tela inicial.",
                on_confirm=self._do_logout,
                confirm_label="Sair",
            )
        else:
            ModalDialog(
                self._parent,
                title="Encerrar Sessão",
                message="Deseja sair? Suas credenciais serão removidas da sessão atual.",
                on_confirm=self._do_logout,
                confirm_label="Sair",
            )

    def _do_logout(self) -> None:
        from state import AppState
        AppState.clear()
        self._demo_banner.grid_remove()
        self._demo_banner_shown = False
        self._parent.show_page("HomePage")

    def _exit_demo_to_register(self) -> None:
        from state import AppState
        AppState.clear()
        self._demo_banner.grid_remove()
        self._demo_banner_shown = False
        self._parent.show_page("RegisterPage")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _clear(self, frame) -> None:
        for w in frame.winfo_children():
            w.destroy()

    @staticmethod
    def _fmt_size(n: int) -> str:
        if n < 1024:     return f"{n} B"
        if n < 1024**2:  return f"{n/1024:.1f} KB"
        if n < 1024**3:  return f"{n/1024**2:.1f} MB"
        return f"{n/1024**3:.1f} GB"
