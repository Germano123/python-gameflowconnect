import customtkinter as ctk
import threading
from ..templates import DefaultLayout
from ..atoms import ButtonComponent, TitleText, SubtitleText, BodyText
from ..molecules import ModalDialog, InputField


class IntegrationsPage(DefaultLayout):
    """
    Page: Conexões e Integrações (Google Drive OAuth e GitHub PAT).
    Movido do Dashboard para gerenciar conexões externas de forma organizada.
    """
    def __init__(self, parent):
        self._parent = parent
        super().__init__(
            parent,
            title="Integrações",
            current_page="IntegrationsPage",
            on_logout=self._on_logout,
        )
        self._build_ui()

    def _build_ui(self) -> None:
        cf = self.content_frame
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_columnconfigure(1, weight=1)

        # Header info
        info_frame = ctk.CTkFrame(cf, fg_color="transparent")
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 10))

        TitleText(info_frame, text="🔗 Conexões & Ferramentas Externas").pack(anchor="w")
        SubtitleText(
            info_frame,
            text="Conecte seu repositório Git e seu Google Drive para sincronizar assets entre artistas e devs.",
        ).pack(anchor="w", pady=(4, 0))

        # --- Google Drive Card ---
        drive_card = ctk.CTkFrame(cf, corner_radius=12, border_width=1, border_color="#2d4a5a", fg_color="#162c38")
        drive_card.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=10)
        drive_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            drive_card,
            text="☁️  Google Drive",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, padx=20, pady=(18, 6), sticky="w")

        BodyText(
            drive_card,
            text="Armazenamento em nuvem utilizado por artistas para entregar imagens, texturas e modelos 3D.",
        ).grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

        self._drive_status_lbl = ctk.CTkLabel(
            drive_card,
            text="Verificando status...",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color="gray60",
        )
        self._drive_status_lbl.grid(row=2, column=0, padx=20, pady=(0, 14), sticky="w")

        ButtonComponent(
            parent=drive_card,
            label="🔑  Autenticar Google Drive (OAuth)",
            size="medium",
            variant="secondary",
            onClick=self._connect_drive,
        ).grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

        # --- GitHub Card ---
        git_card = ctk.CTkFrame(cf, corner_radius=12, border_width=1, border_color="#2d4a5a", fg_color="#162c38")
        git_card.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=10)
        git_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            git_card,
            text="🐙  GitHub",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, padx=20, pady=(18, 6), sticky="w")

        BodyText(
            git_card,
            text="Versionamento de código fonte e scripts do projeto da Game Engine.",
        ).grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

        self._git_status_lbl = ctk.CTkLabel(
            git_card,
            text="Verificando status...",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color="gray60",
        )
        self._git_status_lbl.grid(row=2, column=0, padx=20, pady=(0, 14), sticky="w")

        self._token_input = InputField(
            git_card,
            label="Personal Access Token (PAT)",
            placeholder="ghp_...",
            show="*",
        )
        self._token_input.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        ButtonComponent(
            parent=git_card,
            label="🐙  Conectar GitHub Token",
            size="medium",
            variant="primary",
            onClick=self._connect_github,
        ).grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")

    def on_show(self) -> None:
        self._update_status()

    def _update_status(self) -> None:
        from state import AppState
        if AppState.is_drive_connected():
            self._drive_status_lbl.configure(text="STATUS: Conectado ao Google Drive ✓", text_color="#00aa00")
        else:
            self._drive_status_lbl.configure(text="STATUS: Não conectado ao Google Drive", text_color="gray60")

        if AppState.is_github_connected():
            self._git_status_lbl.configure(text="STATUS: Conectado ao GitHub ✓", text_color="#00aa00")
        else:
            self._git_status_lbl.configure(text="STATUS: Não conectado ao GitHub", text_color="gray60")

    def _connect_drive(self) -> None:
        from services.drive import DriveService
        from state import AppState

        self._drive_status_lbl.configure(text="Abrindo OAuth no navegador...", text_color="#f0c040")

        def run():
            try:
                svc = DriveService()
                svc.authenticate()
                AppState.drive_service = svc
                self.after(0, lambda: self._drive_status_lbl.configure(text="Conectado com sucesso ✓", text_color="#00aa00"))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: self._drive_status_lbl.configure(text=f"Erro: {msg}", text_color="#e74c3c"))

        threading.Thread(target=run, daemon=True).start()

    def _connect_github(self) -> None:
        from services.git_connection import GitService
        from state import AppState

        token = self._token_input.get().strip()
        if not token:
            self._git_status_lbl.configure(text="Insira um token válido", text_color="#e74c3c")
            return

        self._git_status_lbl.configure(text="Verificando token...", text_color="#f0c040")

        def run():
            try:
                svc = GitService(token=token)
                AppState.github_token = token
                AppState.git_service  = svc
                self.after(0, lambda: self._git_status_lbl.configure(text="GitHub Conectado ✓", text_color="#00aa00"))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: self._git_status_lbl.configure(text=f"Erro: {msg}", text_color="#e74c3c"))

        threading.Thread(target=run, daemon=True).start()

    def _on_logout(self) -> None:
        from state import AppState
        AppState.clear()
        self._parent.show_page("HomePage")
