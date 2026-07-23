import customtkinter as ctk
import threading
from tkinter import filedialog
from ..templates import DefaultLayout
from ..atoms import ButtonComponent, TitleText, SubtitleText, BodyText, StatusBadge
from ..molecules import FileCard, ModalDialog, InputField


class WorkspacesPage(DefaultLayout):
    """
    Page: Gestão de Workspaces (Workspaces).
    Permite gerenciar, criar e colaborar em Workspaces.
    Valida a conexão ativa com o Google Drive e suporta a seleção de game engines (Unity e Godot).
    """
    def __init__(self, parent):
        self._parent = parent
        super().__init__(
            parent,
            title="Workspaces",
            current_page="WorkspacesPage",
            on_logout=self._on_logout,
        )
        self._selected_workspace_id = None
        self._build_ui()

    def _build_ui(self) -> None:
        cf = self.content_frame
        cf.grid_columnconfigure(0, weight=1)
        cf.grid_columnconfigure(1, weight=2)
        cf.grid_rowconfigure(1, weight=1)

        # Toolbar
        toolbar = ctk.CTkFrame(cf, fg_color="transparent")
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 10))

        TitleText(toolbar, text="📁 Gestão de Workspaces & Equipes").pack(side="left")

        ButtonComponent(
            parent=toolbar,
            label="➕  Novo Workspace",
            size="small",
            variant="success",
            onClick=self._click_new_workspace,
        ).pack(side="right")

        # Left Column: Workspace List
        left_panel = ctk.CTkFrame(cf, corner_radius=12, border_width=1, border_color="#2d4a5a", fg_color="#162c38")
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        left_panel.grid_rowconfigure(1, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left_panel,
            text="Meus Workspaces",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color="#ffffff",
        ).grid(row=0, column=0, padx=14, pady=12, sticky="w")

        self._workspaces_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        self._workspaces_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        # Right Column: Selected Workspace Detail & Asset Sync
        right_panel = ctk.CTkFrame(cf, corner_radius=12, border_width=1, border_color="#2d4a5a", fg_color="#162c38")
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        right_panel.grid_rowconfigure(2, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        # Workspace header
        self._ws_header_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self._ws_header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=12)

        self._ws_title_lbl = ctk.CTkLabel(
            self._ws_header_frame,
            text="Selecione um Workspace",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color="#ffffff",
        )
        self._ws_title_lbl.pack(anchor="w")

        self._ws_desc_lbl = ctk.CTkLabel(
            self._ws_header_frame,
            text="Clique em um workspace à esquerda para visualizar detalhes e assets.",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="gray60",
            justify="left",
        )
        self._ws_desc_lbl.pack(anchor="w", pady=(2, 0))

        # Workspace Action Toolbar (Invite members & Add asset & Delete)
        self._ws_actions_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self._ws_actions_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

        ButtonComponent(
            parent=self._ws_actions_frame,
            label="👥  Convidar Membro",
            size="small",
            variant="secondary",
            onClick=self._open_invite_modal,
        ).pack(side="left", padx=(0, 8))

        ButtonComponent(
            parent=self._ws_actions_frame,
            label="⬆  Enviar Asset no Workspace (Gerar Alerta)",
            size="small",
            variant="primary",
            onClick=self._upload_asset_to_workspace,
        ).pack(side="left")

        ButtonComponent(
            parent=self._ws_actions_frame,
            label="🗑️  Excluir Workspace",
            size="small",
            variant="danger",
            onClick=self._delete_workspace_action,
        ).pack(side="right")

        # Workspace Assets Scroll
        self._assets_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        self._assets_scroll.grid(row=2, column=0, sticky="nsew", padx=6, pady=6)

    def on_show(self) -> None:
        self._refresh_workspaces()
        # Executar descoberta de workspaces compartilhados em background
        threading.Thread(target=self._discover_shared, daemon=True).start()

    def _discover_shared(self) -> None:
        from state import AppState
        from use_cases import WorkspaceManagerUseCase
        if AppState.is_drive_connected():
            try:
                manager = WorkspaceManagerUseCase()
                discovered = manager.discover_shared_workspaces(AppState.user_email, AppState.drive_service)
                if discovered:
                    self.after(0, self._refresh_workspaces)
            except Exception as e:
                print(f"Erro na descoberta de workspaces em background: {e}")

    def _refresh_workspaces(self) -> None:
        from use_cases import WorkspaceManagerUseCase
        manager = WorkspaceManagerUseCase()
        workspaces = manager.list_workspaces()

        for w in self._workspaces_scroll.winfo_children():
            w.destroy()

        if not workspaces:
            ctk.CTkLabel(self._workspaces_scroll, text="Nenhum workspace criado.").pack(pady=20)
            return

        for ws in workspaces:
            card = ctk.CTkFrame(
                self._workspaces_scroll,
                corner_radius=8,
                border_width=1,
                border_color="#00aa00" if ws.id == self._selected_workspace_id else "#2d4a5a",
                fg_color="#1e3743" if ws.id == self._selected_workspace_id else "#1a3040",
            )
            card.pack(fill="x", padx=4, pady=4)

            row_frame = ctk.CTkFrame(card, fg_color="transparent")
            row_frame.pack(fill="x", padx=10, pady=(8, 2))

            lbl = ctk.CTkLabel(
                row_frame,
                text=f"📁 {ws.name} ({ws.engine})",
                font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
                text_color="#ffffff",
                anchor="w",
            )
            lbl.pack(side="left", fill="x", expand=True)

            from state import AppState
            is_owner = (ws.owner == AppState.user_email)
            badge_text = "Proprietário" if is_owner else "Convidado"
            badge_color = "#00aa00" if is_owner else "#f0a000"

            badge = ctk.CTkLabel(
                row_frame,
                text=badge_text,
                font=ctk.CTkFont(family="Arial", size=9, weight="bold"),
                text_color="#ffffff",
                fg_color=badge_color,
                corner_radius=4,
                width=75,
                height=18
            )
            badge.pack(side="right", padx=(5, 0))

            members_count = len(ws.members)
            sub_lbl = ctk.CTkLabel(
                card,
                text=f"{members_count} colaborador(es)  ·  Criado em {ws.created_at}",
                font=ctk.CTkFont(family="Arial", size=10),
                text_color="gray60",
                anchor="w",
            )
            sub_lbl.pack(fill="x", padx=10, pady=(0, 8))

            card.bind("<Button-1>", lambda _, w_item=ws: self._select_workspace(w_item))
            row_frame.bind("<Button-1>", lambda _, w_item=ws: self._select_workspace(w_item))
            lbl.bind("<Button-1>", lambda _, w_item=ws: self._select_workspace(w_item))
            badge.bind("<Button-1>", lambda _, w_item=ws: self._select_workspace(w_item))
            sub_lbl.bind("<Button-1>", lambda _, w_item=ws: self._select_workspace(w_item))


        if not self._selected_workspace_id and workspaces:
            self._select_workspace(workspaces[0])

    def _select_workspace(self, ws) -> None:
        self._selected_workspace_id = ws.id
        self._ws_title_lbl.configure(text=f"📁 {ws.name}  [Engine: {ws.engine}]")
        members_str = ", ".join(ws.members) if ws.members else ws.owner
        self._ws_desc_lbl.configure(text=f"{ws.description}\nProprietário: {ws.owner}\nMembros: {members_str}")
        self._refresh_workspace_assets(ws)

    def _refresh_workspace_assets(self, ws) -> None:
        from use_cases import WorkspaceManagerUseCase
        from state import AppState

        for w in self._assets_scroll.winfo_children():
            w.destroy()

        # Obter status dinâmico dos assets locais vs remotos no Drive
        manager = WorkspaceManagerUseCase()
        assets = manager.get_workspace_assets_sync_status(ws.id, AppState.drive_service)

        if not assets:
            ctk.CTkLabel(
                self._assets_scroll,
                text="Nenhum asset anexado a este workspace ainda.\nColoque arquivos na pasta local do projeto ou clique em 'Enviar Asset'.",
                font=ctk.CTkFont(family="Arial", size=11),
                text_color="gray50",
            ).pack(pady=40)
            return

        for asset in assets:
            status_txt = "SYNCHRONIZED"
            if asset.status.name == "REMOTE_ONLY":
                status_txt = "Nuvem"
            elif asset.status.name == "LOCAL_ONLY":
                status_txt = "Pendente de Envio"

            card = FileCard(
                self._assets_scroll,
                name=asset.name,
                mime_type=asset.mime_type or "application/octet-stream",
                size=asset.formatted_size,
                modified=asset.modified_time,
                status_text=status_txt,
                on_sync=lambda a=asset: self._sync_asset_action(ws, a),
            )
            card.pack(fill="x", padx=4, pady=3)

    def _sync_asset_action(self, ws, asset) -> None:
        from state import AppState
        from use_cases import WorkspaceManagerUseCase

        if asset.status.name == "SYNCHRONIZED":
            return

        # Executar em segundo plano para não congelar o Tkinter
        def run():
            manager = WorkspaceManagerUseCase()
            success = manager.sync_asset(
                workspace_id=ws.id,
                asset=asset,
                drive_service=AppState.drive_service,
                author_email=AppState.user_email
            )
            if success:
                self.after(0, lambda: ModalDialog(
                    self._parent,
                    title="Sucesso",
                    message=f"Arquivo '{asset.name}' sincronizado com sucesso!",
                    cancel_label="Fechar"
                ))
                self.after(0, lambda: self._refresh_workspace_assets(ws))
            else:
                self.after(0, lambda: ModalDialog(
                    self._parent,
                    title="Erro",
                    message=f"Falha ao sincronizar o arquivo '{asset.name}'.",
                    cancel_label="Fechar"
                ))

        threading.Thread(target=run, daemon=True).start()


    def _click_new_workspace(self) -> None:
        from state import AppState
        # 1. Validar que a conta do Google Drive está conectada
        if not AppState.is_drive_connected():
            ModalDialog(
                self._parent,
                title="⚠️ Google Drive não Conectado",
                message="Você precisa ter sua conta do Google Drive conectada nas 'Integrações' para criar um novo Workspace e autenticar seu e-mail proprietário.",
                cancel_label="Fechar"
            )
            return
        
        self._open_create_workspace_modal()

    def _open_create_workspace_modal(self) -> None:
        modal = ctk.CTkToplevel(self._parent)
        modal.title("Criar Novo Workspace")
        modal.geometry("420x420")
        modal.grab_set()

        ctk.CTkLabel(modal, text="Novo Workspace", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=12)

        name_in = InputField(modal, label="Nome do Workspace", placeholder="Ex: Cyberpunk RPG 2D")
        name_in.pack(padx=20, pady=6, fill="x")

        desc_in = InputField(modal, label="Descrição", placeholder="Ex: Assets e gráficos do chefe final")
        desc_in.pack(padx=20, pady=6, fill="x")

        # Seleção de Engine
        ctk.CTkLabel(
            modal,
            text="Game Engine",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color="#ffffff",
            anchor="w"
        ).pack(padx=20, pady=(6, 2), fill="x")

        engine_var = ctk.StringVar(value="Godot")
        engine_dropdown = ctk.CTkOptionMenu(
            modal,
            variable=engine_var,
            values=["Unity", "Godot", "Unreal (em breve)"],
            fg_color="#1e3743",
            button_color="#2d5266",
            dropdown_fg_color="#162c38",
            dropdown_hover_color="#2d5266",
        )
        engine_dropdown.pack(padx=20, pady=4, fill="x")

        def save():
            from state import AppState
            name = name_in.get().strip()
            desc = desc_in.get().strip()
            engine = engine_var.get()

            if not name:
                return

            if "em breve" in engine:
                ModalDialog(
                    modal,
                    title="Aviso",
                    message="A integração com Unreal Engine está em fase de desenvolvimento e estará disponível em breve!",
                    cancel_label="Entendido"
                )
                return

            from use_cases import WorkspaceManagerUseCase
            manager = WorkspaceManagerUseCase()
            manager.create_workspace(
                name=name,
                description=desc,
                engine=engine,
                owner=AppState.user_email,
                drive_service=AppState.drive_service
            )
            modal.destroy()
            self._refresh_workspaces()

        ButtonComponent(modal, label="Salvar Workspace", variant="success", onClick=save).pack(pady=20)

    def _open_invite_modal(self) -> None:
        if not self._selected_workspace_id:
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
            from use_cases import WorkspaceManagerUseCase
            manager = WorkspaceManagerUseCase()
            manager.share_workspace(self._selected_workspace_id, email, AppState.drive_service)
            modal.destroy()
            ws = manager.get_workspace_by_id(self._selected_workspace_id)
            if ws:
                self._select_workspace(ws)

        ButtonComponent(modal, label="Enviar Convite", variant="primary", onClick=invite).pack(pady=16)

    def _upload_asset_to_workspace(self) -> None:
        if not self._selected_workspace_id:
            return
        path = filedialog.askopenfilename(title="Selecionar Asset")
        if not path:
            return

        name = path.replace("\\", "/").split("/")[-1]
        from domain import Asset
        from state import AppState
        from use_cases import WorkspaceManagerUseCase

        manager = WorkspaceManagerUseCase()
        new_asset = Asset(name=name, local_path=path, size=1024 * 50)

        # Add to workspace and emit alert
        manager.notify_asset_added(
            self._selected_workspace_id,
            AppState.user_email,
            new_asset,
            AppState.drive_service
        )

        ModalDialog(
            self._parent,
            title="🔔 ALERTA DE WORKSPACE EMITIDO!",
            message=f"O asset '{name}' foi enviado ao workspace.\n\nUm alerta visual foi emitido para todos os membros conectados puxarem a atualização!",
            cancel_label="Entendido",
        )

        ws = manager.get_workspace_by_id(self._selected_workspace_id)
        if ws:
            self._refresh_workspace_assets(ws)

    def _delete_workspace_action(self) -> None:
        if not self._selected_workspace_id:
            return
        
        def do_delete():
            from use_cases import WorkspaceManagerUseCase
            manager = WorkspaceManagerUseCase()
            manager.delete_workspace(self._selected_workspace_id)
            self._selected_workspace_id = None
            self._refresh_workspaces()

        ModalDialog(
            self._parent,
            title="Confirmar Exclusão",
            message="Deseja excluir permanentemente este workspace do banco de dados local?",
            on_confirm=do_delete,
            confirm_label="Excluir",
        )

    def _on_logout(self) -> None:
        from state import AppState
        AppState.clear()
        self._parent.show_page("HomePage")
