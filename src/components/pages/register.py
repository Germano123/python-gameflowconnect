import customtkinter as ctk
from ..templates import DefaultLayout
from ..atoms import ButtonComponent
from ..molecules import InputField


class RegisterPage(DefaultLayout):
    """
    Page: first-time setup / account configuration.

    Collects GitHub token and explains how to connect Google Drive.
    """
    def __init__(self, parent):
        self._parent = parent
        super().__init__(
            parent,
            title="GameFlow Connect",
            on_back=lambda: parent.show_page("HomePage"),
        )
        self._build_ui()

    def _build_ui(self) -> None:
        cf = self.content_frame
        cf.grid_rowconfigure(0, weight=1)
        cf.grid_columnconfigure(0, weight=1)

        center = ctk.CTkFrame(cf, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # ── Card ────────────────────────────────────────────────────────
        card = ctk.CTkFrame(
            center,
            corner_radius=16,
            border_width=1,
            border_color="#2d5266",
            width=460,
        )
        card.pack()
        card.grid_columnconfigure(0, weight=1)

        # Header
        header_f = ctk.CTkFrame(card, corner_radius=0, fg_color="#162c38", height=64)
        header_f.grid(row=0, column=0, sticky="ew")
        header_f.grid_propagate(False)
        header_f.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header_f,
            text="⬡  Configuração Inicial",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, padx=24, pady=18, sticky="w")

        # Body
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, padx=28, pady=24, sticky="ew")
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="Configure suas integrações para começar.",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color="gray60",
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Info box
        info = ctk.CTkFrame(body, fg_color="#1a3040", corner_radius=8)
        info.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(
            info,
            text="ℹ  Você precisará de um GitHub Personal Access Token.\n"
                 "Acesse: github.com → Settings → Developer settings → PAT",
            font=ctk.CTkFont(size=11),
            text_color="#7fa8c0",
            justify="left",
            wraplength=380,
        ).pack(padx=12, pady=10, anchor="w")

        # Token field
        self._token_field = InputField(
            body,
            label="GitHub Personal Access Token",
            placeholder="ghp_xxxxxxxxxxxxxxxxxxxx",
            show="*",
        )
        self._token_field.grid(row=2, column=0, sticky="ew", pady=(0, 20))

        # Save button
        ButtonComponent(
            parent=body,
            label="Salvar Token e Continuar →",
            size="medium",
            variant="success",
            onClick=self._on_save,
        ).grid(row=3, column=0, sticky="ew", pady=(0, 10))

        # Status
        self._status = ctk.CTkLabel(
            body,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        )
        self._status.grid(row=4, column=0, pady=(0, 4))

        # Footer
        footer = ctk.CTkFrame(card, corner_radius=0, fg_color="#0f1e26", height=44)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            footer,
            text="Já tenho conta → Fazer Login",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            text_color="gray50",
            hover_color="#162c38",
            command=lambda: self._parent.show_page("LoginPage"),
        ).grid(row=0, column=0, pady=8, padx=16, sticky="e")

    def _on_save(self) -> None:
        from state import AppState
        from services.git_connection import GitService

        token = self._token_field.get().strip()
        if not token:
            self._set_status("Insira um token válido.", "error")
            return

        try:
            svc = GitService(token=token)
            AppState.github_token = token
            AppState.git_service  = svc
            self._set_status("Token salvo com sucesso! ✓", "success")
            self.after(800, lambda: self._parent.show_page("LoginPage"))
        except Exception as e:
            self._set_status(f"Erro: {e}", "error")

    def _set_status(self, msg: str, kind: str = "info") -> None:
        colors = {"error": "#e74c3c", "success": "#00aa00", "info": "#7fa8c0"}
        self._status.configure(text=msg, text_color=colors.get(kind, "gray60"))
