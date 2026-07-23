import customtkinter as ctk
import threading
from tkinter import filedialog
from ..templates import DefaultLayout
from ..atoms import ButtonComponent, TitleText, SubtitleText, BodyText, StatusBadge
from ..molecules import ModalDialog


class ProfilePage(DefaultLayout):
    """
    Page: Perfil do Usuário e Convites de Equipe Recebidos.

    Exibe o e-mail do usuário ativo e busca no Google Drive projetos compartilhados
    com ele (Convites) para que ele possa aceitar e configurar a pasta local de sincronização.
    """
    def __init__(self, parent):
        self._parent = parent
        super().__init__(
            parent,
            title="Perfil",
            current_page="ProfilePage",
            on_logout=self._on_logout,
        )
        self._pending_invites = []
        self._build_ui()

    def _build_ui(self) -> None:
        cf = self.content_frame
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_columnconfigure(1, weight=1)

        # --- Left Panel: User Profile Info ---
        left_panel = ctk.CTkFrame(cf, corner_radius=12, border_width=1, border_color="#2d4a5a", fg_color="#162c38")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        left_panel.grid_columnconfigure(0, weight=1)

        TitleText(left_panel, text="👤 Perfil da Conta").grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self._email_lbl = ctk.CTkLabel(
            left_panel,
            text="E-mail: verificando...",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color="#ffffff"
        )
        self._email_lbl.grid(row=1, column=0, padx=20, pady=6, sticky="w")

        self._db_lbl = ctk.CTkLabel(
            left_panel,
            text="Banco SQLite Local: Conectado (gameflow_local.db)",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="#00aa00"
        )
        self._db_lbl.grid(row=2, column=0, padx=20, pady=6, sticky="w")

        # --- Right Panel: Pending Team Invitations (Convites Recebidos) ---
        right_panel = ctk.CTkFrame(cf, corner_radius=12, border_width=1, border_color="#2d4a5a", fg_color="#162c38")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        TitleText(right_panel, text="📩 Convites de Projetos Recebidos").grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self._invites_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        self._invites_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def on_show(self) -> None:
        from state import AppState
        self._email_lbl.configure(text=f"E-mail Ativo: {AppState.user_email}")
        self._refresh_invitations()

    def _refresh_invitations(self) -> None:
        for w in self._invites_scroll.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self._invites_scroll,
            text="Buscando novos convites compartilhados no Drive...",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="gray60"
        ).pack(pady=20)

        threading.Thread(target=self._fetch_drive_invites, daemon=True).start()

    def _fetch_drive_invites(self) -> None:
        from state import AppState
        from use_cases import ProjectManagerUseCase
        
        self._pending_invites = []
        if not AppState.is_drive_connected():
            self.after(0, lambda: self._render_empty_invites("Google Drive não conectado em Integrações."))
            return

        try:
            # 1. Buscar convites no Drive
            drive_service = AppState.drive_service
            shared_files = drive_service.search_shared_projects()
            
            manager = ProjectManagerUseCase()
            local_projects = {p.id for p in manager.list_projects()}

            for file_info in shared_files:
                file_id = file_info.get("id")
                parents = file_info.get("parents")
                if not parents:
                    continue
                drive_folder_id = parents[0]

                # Ler o manifesto do projeto compartilhado no Drive
                metadata = drive_service.read_json_file(file_id)
                proj_id = metadata.get("id")
                members = metadata.get("members", [])

                # Se o usuário faz parte e o projeto não está adicionado localmente, é um convite pendente!
                if AppState.user_email in members and proj_id not in local_projects:
                    self._pending_invites.append({
                        "id": proj_id,
                        "name": metadata.get("name", "Sem nome"),
                        "description": metadata.get("description", "Sem descrição"),
                        "owner": metadata.get("owner", "Desconhecido"),
                        "drive_folder_id": drive_folder_id,
                        "members": members,
                        "created_at": metadata.get("created_at", "")
                    })

            self.after(0, self._render_invites)
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self._render_empty_invites(f"Erro ao buscar convites: {msg}"))

    def _render_empty_invites(self, message: str) -> None:
        for w in self._invites_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self._invites_scroll,
            text=message,
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="gray50"
        ).pack(pady=40)

    def _render_invites(self) -> None:
        for w in self._invites_scroll.winfo_children():
            w.destroy()

        if not self._pending_invites:
            ctk.CTkLabel(
                self._invites_scroll,
                text="Nenhum convite pendente encontrado no seu Drive.",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color="gray50"
            ).pack(pady=40)
            return

        for invite in self._pending_invites:
            card = ctk.CTkFrame(self._invites_scroll, corner_radius=8, fg_color="#1a3040", border_width=1, border_color="#2d4a5a")
            card.pack(fill="x", padx=4, pady=4)

            ctk.CTkLabel(
                card,
                text=f"📁 Convite: {invite['name']}",
                font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
                text_color="#ffffff",
                anchor="w"
            ).pack(fill="x", padx=12, pady=(8, 2))

            ctk.CTkLabel(
                card,
                text=f"Proprietário: {invite['owner']}\nDescrição: {invite['description']}",
                font=ctk.CTkFont(family="Arial", size=10),
                text_color="gray60",
                anchor="w",
                justify="left"
            ).pack(fill="x", padx=12, pady=(0, 6))

            # Ações de Aceitar / Recusar
            btn_row = ctk.CTkFrame(card, fg_color="transparent")
            btn_row.pack(fill="x", padx=12, pady=(0, 8))

            ButtonComponent(
                parent=btn_row,
                label="✓ Aceitar e Adicionar",
                size="small",
                variant="success",
                onClick=lambda inv=invite: self._accept_invite(inv),
            ).pack(side="left", padx=(0, 8))

    def _accept_invite(self, invite: dict) -> None:
        # Pedir diretório local de sincronização da engine
        local_dir = filedialog.askdirectory(title=f"Selecionar pasta local para sincronizar {invite['name']}")
        if not local_dir:
            return

        # Gravar no SQLite local
        import sqlite3
        from adapters.database import LocalDatabase
        db = LocalDatabase()
        
        try:
            with db.get_connection() as conn:
                conn.execute(
                    "INSERT INTO local_projects (id, name, description, drive_folder_id, local_path, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (invite["id"], invite["name"], invite["description"], invite["drive_folder_id"], local_dir, invite["owner"], invite["created_at"])
                )
                conn.commit()

            ModalDialog(
                self._parent,
                title="Projeto Adicionado!",
                message=f"O projeto '{invite['name']}' foi sincronizado localmente na pasta:\n{local_dir}",
                cancel_label="Entendido"
            )
            self._refresh_invitations()
        except sqlite3.IntegrityError:
            ModalDialog(
                self._parent,
                title="Aviso",
                message="Este projeto já está sincronizado em sua máquina.",
                cancel_label="Fechar"
            )
        except Exception as e:
            ModalDialog(
                self._parent,
                title="Erro",
                message=f"Erro ao salvar projeto localmente: {e}",
                cancel_label="Fechar"
            )

    def _on_logout(self) -> None:
        from state import AppState
        AppState.clear()
        self._parent.show_page("HomePage")
