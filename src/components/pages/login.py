import customtkinter as ctk
import threading
from ..templates import DefaultLayout
from ..atoms import ButtonComponent
from ..molecules import InputField


class LoginPage(DefaultLayout):
    """
    Page: authentication screen.

    Users enter a GitHub PAT and optionally connect Google Drive.
    On success, navigates to DashboardPage.
    """
    def __init__(self, parent):
        self._parent = parent
        super().__init__(parent, title="GameFlow Connect", on_logout=None)
        self._build_ui()

    def _build_ui(self) -> None:
        cf = self.content_frame
        cf.grid_rowconfigure(0, weight=1)
        cf.grid_columnconfigure(0, weight=1)

        # ── Outer centering frame ────────────────────────────────────────
        center = ctk.CTkFrame(cf, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # ── Card ────────────────────────────────────────────────────────
        card = ctk.CTkFrame(
            center,
            corner_radius=16,
            border_width=1,
            border_color="#2d5266",
            width=420,
        )
        card.pack()
        card.grid_columnconfigure(0, weight=1)

        # Header row
        header_f = ctk.CTkFrame(card, corner_radius=0, fg_color="#162c38", height=64)
        header_f.grid(row=0, column=0, sticky="ew")
        header_f.grid_propagate(False)
        header_f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_f,
            text="⬡  Acesso à Plataforma",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, padx=24, pady=18, sticky="w")

        # Body
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, padx=28, pady=24, sticky="ew")
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="Conecte suas contas para continuar",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color="gray60",
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        # GitHub token input
        self._token_field = InputField(
            body,
            label="GitHub Personal Access Token",
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx",
            show="*",
        )
        self._token_field.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        # GitHub button
        ButtonComponent(
            parent=body,
            label="🐙  Entrar com GitHub Token",
            size="medium",
            variant="primary",
            onClick=self._on_github_login,
        ).grid(row=2, column=0, sticky="ew", pady=(0, 10))

        # Drive button
        ButtonComponent(
            parent=body,
            label="☁  Conectar Google Drive (OAuth)",
            size="medium",
            variant="secondary",
            onClick=self._on_drive_login,
        ).grid(row=3, column=0, sticky="ew", pady=(0, 4))

        # Divider
        ctk.CTkFrame(body, height=1, fg_color="gray30", corner_radius=0).grid(
            row=4, column=0, sticky="ew", pady=16
        )

        # Status label
        self._status = ctk.CTkLabel(
            body,
            text="",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="gray60",
            wraplength=360,
        )
        self._status.grid(row=5, column=0, pady=(0, 4))

        # Progress bar (hidden initially)
        self._progress = ctk.CTkProgressBar(body, mode="indeterminate", height=4)
        self._progress.grid(row=6, column=0, sticky="ew")
        self._progress.grid_remove()

        # Footer
        footer = ctk.CTkFrame(card, corner_radius=0, fg_color="#0f1e26", height=44)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            footer,
            text="← Voltar à página inicial",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            text_color="gray50",
            hover_color="#162c38",
            command=lambda: self._parent.show_page("HomePage"),
        ).grid(row=0, column=0, columnspan=2, pady=8, padx=16, sticky="ew")


    def on_show(self) -> None:
        """Chamado quando a tela de login é exibida. Tenta login automático com as credenciais salvas."""
        import os
        from state import AppState
        from use_cases import UserProfileUseCase
        from services.drive import DriveService, TOKEN_PATH
        from services.git_connection import GitService

        uc = UserProfileUseCase()
        profile = uc.get_last_active_profile()

        # Se houver token do Drive salvo localmente, tentar login automático
        if os.path.exists(TOKEN_PATH) and profile:
            self._set_status("Sessão salva encontrada. Conectando automaticamente...", "info")
            self._show_progress(True)

            def auto_login():
                try:
                    # 1. Reconectar Drive
                    svc = DriveService()
                    svc.authenticate()
                    AppState.drive_service = svc
                    try:
                        AppState.user_email = svc.get_user_email()
                    except Exception:
                        AppState.user_email = profile.email

                    self.after(0, lambda: self._set_status("Google Drive reconectado ✓", "success"))

                    # 2. Reconectar GitHub (se houver token salvo)
                    if profile.github_token:
                        try:
                            git_svc = GitService(token=profile.github_token)
                            AppState.github_token = profile.github_token
                            AppState.git_service = git_svc
                            self.after(0, lambda: self._set_status("GitHub reconectado ✓", "success"))
                        except Exception as ge:
                            print(f"Erro auto-login GitHub: {ge}")

                    # Redirecionar
                    self.after(500, lambda: self._parent.show_page("DashboardPage"))
                except Exception as e:
                    print(f"Erro auto-login: {e}")
                    self.after(0, lambda: self._set_status("Sessão anterior expirada. Faça login novamente.", "info"))
                finally:
                    self.after(0, lambda: self._show_progress(False))

            threading.Thread(target=auto_login, daemon=True).start()


    def _on_github_login(self) -> None:
        from state import AppState
        from services.git_connection import GitService

        token = self._token_field.get().strip()
        if not token:
            self._set_status("Insira um token válido.", "error")
            return

        self._set_status("Autenticando no GitHub...", "info")
        self._show_progress(True)

        def run():
            try:
                svc = GitService(token=token)
                AppState.github_token = token
                AppState.git_service  = svc
                self.after(0, lambda: self._set_status("GitHub conectado ✓", "success"))
                self.after(0, self._check_ready)
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: self._set_status(f"Erro GitHub: {msg}", "error"))
            finally:
                self.after(0, lambda: self._show_progress(False))

        threading.Thread(target=run, daemon=True).start()

    def _on_drive_login(self) -> None:
        from services.drive import DriveService
        from state import AppState

        self._set_status("Abrindo navegador para Google OAuth...", "info")
        self._show_progress(True)

        def run():
            try:
                svc = DriveService()
                svc.authenticate()
                AppState.drive_service = svc
                try:
                    AppState.user_email = svc.get_user_email()
                except Exception:
                    pass
                self.after(0, lambda: self._set_status("Google Drive conectado ✓", "success"))
                self.after(0, self._check_ready)

            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: self._set_status(f"Erro Drive: {msg}", "error"))
            finally:
                self.after(0, lambda: self._show_progress(False))


        threading.Thread(target=run, daemon=True).start()

    def _check_ready(self) -> None:
        from state import AppState
        from use_cases import UserProfileUseCase
        if AppState.is_drive_connected() or AppState.is_github_connected():
            if AppState.is_drive_connected():
                try:
                    uc = UserProfileUseCase()
                    profile = uc.get_profile(AppState.user_email)
                    if not profile:
                        uc.save_profile(AppState.user_email, username="Usuário GameFlow", bio="", github_token=AppState.github_token)
                    elif AppState.github_token:
                        uc.save_profile(AppState.user_email, profile.username, profile.bio, github_token=AppState.github_token)
                except Exception as ex:
                    print(f"Erro ao salvar perfil ao logar: {ex}")

            self._set_status("Conexão realizada com sucesso! Entrando...", "success")
            self.after(600, lambda: self._parent.show_page("DashboardPage"))



    def _set_status(self, msg: str, kind: str = "info") -> None:
        colors = {"error": "#e74c3c", "success": "#00aa00", "info": "#7fa8c0"}
        self._status.configure(text=msg, text_color=colors.get(kind, "gray60"))

    def _show_progress(self, show: bool) -> None:
        if show:
            self._progress.grid()
            self._progress.start()
        else:
            self._progress.stop()
            self._progress.grid_remove()
