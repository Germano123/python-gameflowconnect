import customtkinter as ctk
import threading
from tkinter import filedialog
from ..templates import DefaultLayout
from ..atoms import ButtonComponent, TitleText, SubtitleText, BodyText, StatusBadge
from ..molecules import FileCard, ModalDialog, InputField


class ProjectsPage(DefaultLayout):
    """
    Page: Gestão de Projetos (Projetos).
    Permite criar novos projetos, convidar outros usuários para colaboração e
    anexar assets gerando um ALERTA VISUAL de atualização para a equipe.
    """
    def __init__(self, parent):
        self._parent = parent
        super().__init__(
            parent,
            title="Projetos",
            current_page="ProjectsPage",
            on_logout=self._on_logout,
        )
        self._selected_project_id = None
        self._build_ui()

    def _build_ui(self) -> None:
        cf = self.content_frame
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_columnconfigure(1, weight=2)
        cf.grid_rowconfigure(1, weight=1)

        # Toolbar
        toolbar = ctk.CTkFrame(cf, fg_color="transparent")
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 10))

        TitleText(toolbar, text="📁 Gestão de Projetos & Equipes").pack(side="left")

        ButtonComponent(
            parent=toolbar,
            label="➕  Novo Projeto",
            size="small",
            variant="success",
            onClick=self._open_create_project_modal,
        ).pack(side="right")

        # Left Column: Project List
        left_panel = ctk.CTkFrame(cf, corner_radius=12, border_width=1, border_color="#2d4a5a", fg_color="#162c38")
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        left_panel.grid_rowconfigure(1, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left_panel,
            text="Meus Projetos",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, padx=14, pady=12, sticky="w")

        self._projects_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self._projects_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        # Right Column: Selected Project Detail & Asset Sync
        right_panel = ctk.CTkFrame(cf, corner_radius=12, border_width=1, border_color="#2d4a5a", fg_color="#162c38")
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        right_panel.grid_rowconfigure(2, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        # Project header
        self._proj_header_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self._proj_header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=12)

        self._proj_title_lbl = ctk.CTkLabel(
            self._proj_header_frame,
            text="Selecione um projeto",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color="#ffffff",
        )
        self._proj_title_lbl.pack(anchor="w")

        self._proj_desc_lbl = ctk.CTkLabel(
            self._proj_header_frame,
            text="Clique em um projeto à esquerda para visualizar detalhes e assets.",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="gray60",
        )
        self._proj_desc_lbl.pack(anchor="w", pady=(2, 0))

        # Project Action Toolbar (Invite members & Add asset & Delete)
        self._proj_actions_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self._proj_actions_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

        ButtonComponent(
            parent=self._proj_actions_frame,
            label="👥  Convidar Membro",
            size="small",
            variant="secondary",
            onClick=self._open_invite_modal,
        ).pack(side="left", padx=(0, 8))

        ButtonComponent(
            parent=self._proj_actions_frame,
            label="⬆  Enviar Asset no Projeto (Gerar Alerta)",
            size="small",
            variant="primary",
            onClick=self._upload_asset_to_project,
        ).pack(side="left")

        ButtonComponent(
            parent=self._proj_actions_frame,
            label="🗑️  Excluir Projeto",
            size="small",
            variant="danger",
            onClick=self._delete_project_action,
        ).pack(side="right")

        # Project Assets Scroll
        self._assets_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        self._assets_scroll.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)


    def on_show(self) -> None:
        self._refresh_projects()
        # Executar descoberta de projetos compartilhados em background
        threading.Thread(target=self._discover_shared, daemon=True).start()

    def _discover_shared(self) -> None:
        from state import AppState
        from use_cases import ProjectManagerUseCase
        if AppState.is_drive_connected():
            try:
                manager = ProjectManagerUseCase()
                discovered = manager.discover_shared_projects(AppState.user_email, AppState.drive_service)
                if discovered:
                    self.after(0, self._refresh_projects)
            except Exception as e:
                print(f"Erro na descoberta em background: {e}")

    def _refresh_projects(self) -> None:
        from use_cases import ProjectManagerUseCase
        manager = ProjectManagerUseCase()
        projects = manager.list_projects()

        for w in self._projects_scroll.winfo_children():
            w.destroy()

        if not projects:
            ctk.CTkLabel(self._projects_scroll, text="Nenhum projeto criado.").pack(pady=20)
            return

        for proj in projects:
            card = ctk.CTkFrame(
                self._projects_scroll,
                corner_radius=8,
                border_width=1,
                border_color="#00aa00" if proj.id == self._selected_project_id else "#2d4a5a",
                fg_color="#1e3743" if proj.id == self._selected_project_id else "#1a3040",
            )
            card.pack(fill="x", padx=4, pady=4)

            lbl = ctk.CTkLabel(
                card,
                text=f"📁 {proj.name}",
                font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
                text_color="#ffffff",
                anchor="w",
            )
            lbl.pack(fill="x", padx=10, pady=(8, 2))

            members_count = len(proj.members)
            sub_lbl = ctk.CTkLabel(
                card,
                text=f"{members_count} colaborador(es)  ·  Criado em {proj.created_at}",
                font=ctk.CTkFont(family="Arial", size=10),
                text_color="gray60",
                anchor="w",
            )
            sub_lbl.pack(fill="x", padx=10, pady=(0, 8))

            card.bind("<Button-1>", lambda _, p=proj: self._select_project(p))
            lbl.bind("<Button-1>", lambda _, p=proj: self._select_project(p))
            sub_lbl.bind("<Button-1>", lambda _, p=proj: self._select_project(p))

        if not self._selected_project_id and projects:
            self._select_project(projects[0])

    def _select_project(self, proj) -> None:
        self._selected_project_id = proj.id
        self._proj_title_lbl.configure(text=f"📁 {proj.name}")
        members_str = ", ".join(proj.members) if proj.members else proj.owner
        self._proj_desc_lbl.configure(text=f"{proj.description}\nMembros: {members_str}")
        self._refresh_project_assets(proj)

    def _refresh_project_assets(self, proj) -> None:
        for w in self._assets_scroll.winfo_children():
            w.destroy()

        if not proj.assets:
            ctk.CTkLabel(
                self._assets_scroll,
                text="Nenhum asset anexado a este projeto ainda.\nClique em 'Enviar Asset' acima para anexar mídias e alertar a equipe.",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color="gray50",
            ).pack(pady=40)
            return

        for asset in proj.assets:
            card = FileCard(
                self._assets_scroll,
                name=asset.name,
                mime_type=asset.mime_type or "image/png",
                size=asset.formatted_size,
                modified=asset.modified_time,
                status_text="PROJETO_ATIVO",
            )
            card.pack(fill="x", padx=4, pady=3)

    def _open_create_project_modal(self) -> None:
        modal = ctk.CTkToplevel(self._parent)
        modal.title("Criar Novo Projeto")
        modal.geometry("400x320")
        modal.grab_set()

        ctk.CTkLabel(modal, text="Criar Projeto", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=12)

        name_in = InputField(modal, label="Nome do Projeto", placeholder="Ex: Cyberpunk RPG 2D")
        name_in.pack(padx=20, pady=6, fill="x")

        desc_in = InputField(modal, label="Descrição", placeholder="Ex: Assets e gráficos do chefe final")
        desc_in.pack(padx=20, pady=6, fill="x")

        def save():
            from state import AppState
            name = name_in.get().strip()
            desc = desc_in.get().strip()
            if not name:
                return
            from use_cases import ProjectManagerUseCase
            manager = ProjectManagerUseCase()
            manager.create_project(
                name=name,
                description=desc,
                owner=AppState.user_email,
                drive_service=AppState.drive_service
            )
            modal.destroy()
            self._refresh_projects()

        ButtonComponent(modal, label="Salvar Projeto", variant="success", onClick=save).pack(pady=16)

    def _open_invite_modal(self) -> None:
        if not self._selected_project_id:
            return
        modal = ctk.CTkToplevel(self._parent)
        modal.title("Convidar Colaborador")
        modal.geometry("380x240")
        modal.grab_set()

        ctk.CTkLabel(modal, text="Convidar Membro", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=12)
        email_in = InputField(modal, label="E-mail ou Usuário", placeholder="artista@estudio.io")
        email_in.pack(padx=20, pady=6, fill="x")

        def invite():
            from state import AppState
            email = email_in.get().strip()
            if not email:
                return
            from use_cases import ProjectManagerUseCase
            manager = ProjectManagerUseCase()
            manager.share_project(self._selected_project_id, email, AppState.drive_service)
            modal.destroy()
            proj = manager.get_project_by_id(self._selected_project_id)
            if proj:
                self._select_project(proj)

        ButtonComponent(modal, label="Enviar Convite", variant="primary", onClick=invite).pack(pady=16)

    def _upload_asset_to_project(self) -> None:
        if not self._selected_project_id:
            return
        path = filedialog.askopenfilename(title="Selecionar Asset do Projeto")
        if not path:
            return

        name = path.replace("\\", "/").split("/")[-1]
        from domain import Asset
        from state import AppState
        from use_cases import ProjectManagerUseCase

        manager = ProjectManagerUseCase()
        new_asset = Asset(name=name, local_path=path, size=1024 * 50)

        # Add to project and emit visual alert
        notif = manager.notify_asset_added(
            self._selected_project_id,
            AppState.user_email,
            new_asset,
            AppState.drive_service
        )

        # Show visual alert dialog on upload
        ModalDialog(
            self._parent,
            title="🔔 ALERTA DE PROJETO EMITIDO!",
            message=f"O asset '{name}' foi enviado ao projeto.\n\nUm alerta visual foi emitido para todos os membros conectados puxarem a atualização!",
            cancel_label="Entendido",
        )

        proj = manager.get_project_by_id(self._selected_project_id)
        if proj:
            self._refresh_project_assets(proj)

    def _delete_project_action(self) -> None:
        if not self._selected_project_id:
            return
        
        def do_delete():
            from use_cases import ProjectManagerUseCase
            manager = ProjectManagerUseCase()
            manager.delete_project(self._selected_project_id)
            self._selected_project_id = None
            self._refresh_projects()

        ModalDialog(
            self._parent,
            title="Confirmar Exclusão",
            message="Deseja excluir permanentemente este projeto do banco de dados local?",
            on_confirm=do_delete,
            confirm_label="Excluir",
        )

    def _on_logout(self) -> None:
        from state import AppState
        AppState.clear()
        self._parent.show_page("HomePage")

