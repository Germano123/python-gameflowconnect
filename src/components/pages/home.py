import customtkinter as ctk
from ..atoms import ButtonComponent


class HomePage(ctk.CTkFrame):
    """
    Page: landing/welcome screen.

    Offers three entry points:
      1. Entrar  → LoginPage (full integration)
      2. Experimentar Demo → enters demo mode directly
      3. Configurar pela primeira vez → RegisterPage
    """
    def __init__(self, parent):
        super().__init__(parent, corner_radius=0, fg_color="#0f1e26")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Background decorative circles ───────────────────────────────
        canvas_bg = ctk.CTkCanvas(self, bg="#0f1e26", highlightthickness=0)
        canvas_bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.after(50, lambda: self._draw_bg(canvas_bg))

        # ── Central card ────────────────────────────────────────────────
        card = ctk.CTkFrame(
            self,
            corner_radius=20,
            fg_color="#1e3743",
            border_width=1,
            border_color="#2d5266",
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.grid_columnconfigure(0, weight=1)

        # Logo icon
        ctk.CTkLabel(
            card,
            text="⬡",
            font=ctk.CTkFont(size=52),
            text_color="#00aa00",
        ).grid(row=0, column=0, pady=(36, 0))

        # App title
        ctk.CTkLabel(
            card,
            text="GameFlow Connect",
            font=ctk.CTkFont(family="Arial", size=34, weight="bold"),
            text_color="#ffffff",
        ).grid(row=1, column=0, padx=60, pady=(8, 0))

        # Accent separator
        ctk.CTkFrame(card, height=3, corner_radius=2, fg_color="#00aa00").grid(
            row=2, column=0, sticky="ew", padx=60, pady=(12, 0)
        )

        # Tagline
        ctk.CTkLabel(
            card,
            text="Colaboração entre artistas e programadores de jogos",
            font=ctk.CTkFont(family="Arial", size=13),
            text_color="#7fa8c0",
        ).grid(row=3, column=0, padx=60, pady=(14, 0))

        # Version badge
        ctk.CTkLabel(
            card,
            text="v2.0.0  ·  Alpha",
            font=ctk.CTkFont(family="Arial", size=10),
            text_color="#4a7a94",
        ).grid(row=4, column=0, pady=(6, 0))


        # ── Primary action: full login ───────────────────────────────────
        ButtonComponent(
            parent=card,
            label="  Entrar com minhas contas  →",
            size="large",
            variant="success",
            width=260,
            onClick=lambda: parent.show_page("LoginPage"),
        ).grid(row=5, column=0, pady=(28, 36))


    def _draw_bg(self, canvas) -> None:
        """Draws subtle decorative circles on the background canvas."""
        w = self.winfo_width()
        h = self.winfo_height()
        canvas.create_oval(w - 320, -80, w + 80,  320, outline="#1e3743", width=2)
        canvas.create_oval(w - 240, -40, w + 40,  280, outline="#1a2e38", width=1)
        canvas.create_oval(-80,  h - 280, 280, h + 80, outline="#1e3743", width=2)
