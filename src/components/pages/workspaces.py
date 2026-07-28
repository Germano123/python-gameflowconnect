import customtkinter as ctk
import threading
import os
import shutil
from tkinter import filedialog
from ..templates import DefaultLayout
from ..atoms import ButtonComponent, TitleText, SubtitleText, BodyText, StatusBadge
from ..molecules import FileCard, ModalDialog, InputField


class InputDialog(ctk.CTkToplevel):
    """
    Componente Molecule: Uma caixa de diálogo modal de input com design consistente.
    """
    def __init__(self, parent, title: str, prompt: str, callback, initial_value: str = ""):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x180")
        self.grab_set()
        self.resizable(False, False)

        # Centralizar na tela pai
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 180) // 2
        self.geometry(f"+{x}+{y}")

        ctk.CTkLabel(self, text=prompt, font=ctk.CTkFont(family="Arial", size=12, weight="bold"), text_color="#ffffff").pack(pady=(20, 8))
        
        self.entry = ctk.CTkEntry(self, width=280, fg_color="#13232c", border_color="#2d4a5a", text_color="#ffffff")
        self.entry.pack(pady=6)
        self.entry.insert(0, initial_value)
        self.entry.focus()

        def confirm():
            val = self.entry.get().strip()
            if val:
                callback(val)
            self.destroy()

        ButtonComponent(self, label="Confirmar", variant="success", onClick=confirm).pack(pady=(12, 12))


class WorkspacesPage(DefaultLayout):
    """
    Page: Gestão de Workspaces (Workspaces) e Explorador de Arquivos.
    Permite gerenciar, criar, navegar em pastas, gerenciar arquivos/pastas
    e sincronizar assets diretamente com o Drive.
    """
    def __init__(self, parent):
        self._parent = parent
        self._current_subpath = ""
        self._uploading_files = set()  # Set de caminhos relativos em upload ativo
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

        TitleText(toolbar, text="📁 Gestão de Workspaces & Equipes").pack(side="top", anchor="w")

        # Campo editável de diretório base (Documents por padrão)
        base_dir_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        base_dir_frame.pack(fill="x", pady=(8, 0), anchor="w")

        ctk.CTkLabel(
            base_dir_frame,
            text="Diretório Base Local:",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color="gray60",
        ).pack(side="left", padx=(0, 6))

        from state import AppState
        self._base_dir_var = ctk.StringVar(value=AppState.local_base_dir)
        self._base_dir_var.trace_add("write", lambda *args: setattr(AppState, "local_base_dir", self._base_dir_var.get()))

        self._base_dir_entry = ctk.CTkEntry(
            base_dir_frame,
            textvariable=self._base_dir_var,
            width=360,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#13232c",
            border_color="#2d4a5a",
            text_color="#ffffff"
        )
        self._base_dir_entry.pack(side="left", padx=(0, 8))

        def browse_base_dir():
            chosen = filedialog.askdirectory(
                title="Selecionar Diretório Base",
                initialdir=self._base_dir_var.get()
            )
            if chosen:
                self._base_dir_var.set(chosen)
                AppState.local_base_dir = chosen


        ButtonComponent(
            parent=base_dir_frame,
            label="📁 Alterar...",
            size="small",
            variant="primary",
            onClick=browse_base_dir,
        ).pack(side="left", padx=(0, 20))

        ButtonComponent(
            parent=toolbar,
            label="➕  Novo Workspace",
            size="small",
            variant="success",
            onClick=self._click_new_workspace,
        ).pack(side="right", pady=(0, 10))

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
        self._refresh_workspaces(scan=True)
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
                    self.after(0, lambda: self._refresh_workspaces(scan=True))
            except Exception as e:
                print(f"Erro na descoberta de workspaces em background: {e}")


    def _refresh_workspaces(self, scan: bool = False) -> None:
        from use_cases import WorkspaceManagerUseCase
        from state import AppState
        manager = WorkspaceManagerUseCase()
        
        # Escanear e importar automaticamente workspaces existentes no PC antes de listar
        if scan and hasattr(AppState, "local_base_dir") and AppState.local_base_dir:
            try:
                manager.scan_and_import_local_workspaces(AppState.local_base_dir)
            except Exception as e:
                print(f"Erro ao escanear workspaces locais: {e}")
                
        workspaces = manager.list_workspaces()


        for w in self._workspaces_scroll.winfo_children():
            w.destroy()

        if not workspaces:
            ctk.CTkLabel(self._workspaces_scroll, text="Nenhum workspace criado.").pack(pady=20)
            self._clear_workspace_details()
            return

        for ws in workspaces:
            is_selected = (ws.id == self._selected_workspace_id)
            normal_bg = "#1e3743" if is_selected else "#1a3040"
            hover_bg = "#244252" if is_selected else "#21394c"
            pressed_bg = "#152530" if is_selected else "#11202b"
            
            normal_border = "#00aa00" if is_selected else "#2d4a5a"
            hover_border = "#00ff00" if is_selected else "#4a6e84"

            card = ctk.CTkFrame(
                self._workspaces_scroll,
                corner_radius=8,
                border_width=1,
                border_color=normal_border,
                fg_color=normal_bg,
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

            # Efeitos visuais de hover, click e seleção
            def on_enter(e, card_widget=card, border=hover_border, bg=hover_bg):
                if card_widget.winfo_exists():
                    card_widget.configure(border_color=border, fg_color=bg)

            def on_leave(e, card_widget=card, border=normal_border, bg=normal_bg):
                if card_widget.winfo_exists():
                    card_widget.configure(border_color=border, fg_color=bg)

            def on_press(e, card_widget=card, bg=pressed_bg):
                if card_widget.winfo_exists():
                    card_widget.configure(fg_color=bg)

            # Bindings recursivos em todos os elementos do card
            widgets_to_bind = [card, row_frame, lbl, badge, sub_lbl]
            for widget in widgets_to_bind:
                widget.bind("<Enter>", lambda e: on_enter(e))
                widget.bind("<Leave>", lambda e: on_leave(e))
                widget.bind("<Button-1>", lambda e, w_item=ws: (on_press(e), self._select_workspace(w_item)))

        if not self._selected_workspace_id and workspaces:
            self._select_workspace(workspaces[0])


    def _clear_workspace_details(self) -> None:
        self._selected_workspace_id = None
        self._current_subpath = ""
        self._ws_title_lbl.configure(text="Selecione um Workspace")
        self._ws_desc_lbl.configure(text="Clique em um workspace à esquerda para visualizar detalhes e assets.")
        for w in self._assets_scroll.winfo_children():
            w.destroy()

    def _select_workspace(self, ws) -> None:
        self._selected_workspace_id = ws.id
        self._current_subpath = ""  # Sempre resetar para a raiz ao trocar de workspace
        self._ws_title_lbl.configure(text=f"📁 {ws.name}  [Engine: {ws.engine}]")
        members_str = ", ".join(ws.members) if ws.members else ws.owner
        self._ws_desc_lbl.configure(text=f"{ws.description}\nProprietário: {ws.owner}\nMembros: {members_str}")
        self._refresh_workspace_assets(ws)
        self.after(10, lambda: self._refresh_workspaces(scan=False))



    def _refresh_workspace_assets(self, ws) -> None:
        from use_cases import WorkspaceManagerUseCase
        from state import AppState
        import threading

        # Limpar área de assets
        for w in self._assets_scroll.winfo_children():
            w.destroy()

        # 1. ── Barra de Navegação Superior (Sempre visível para resposta imediata) ───────────────────────────────
        nav_bar = ctk.CTkFrame(self._assets_scroll, fg_color="transparent")
        nav_bar.pack(fill="x", padx=4, pady=(0, 8))

        path_display = f"Raiz / {self._current_subpath.replace('\\', ' / ')}" if self._current_subpath else "Raiz"
        ctk.CTkLabel(
            nav_bar,
            text=f"📍 {path_display}",
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            text_color="#ffffff",
        ).pack(side="left")

        # Botão Nova Pasta
        ButtonComponent(
            parent=nav_bar,
            label="📁 Nova Pasta",
            size="small",
            variant="success",
            onClick=lambda: self._create_folder_prompt(ws),
        ).pack(side="right", padx=(8, 0))

        if self._current_subpath:
            ButtonComponent(
                parent=nav_bar,
                label="⬆️ Voltar",
                size="small",
                variant="secondary",
                onClick=lambda: self._go_back_directory(ws),
            ).pack(side="right")

        # 2. Indicador de carregamento
        loading_frame = ctk.CTkFrame(self._assets_scroll, fg_color="transparent")
        loading_frame.pack(fill="both", expand=True, pady=40)
        
        ctk.CTkLabel(
            loading_frame,
            text="⏳ Sincronizando com o Google Drive...",
            font=ctk.CTkFont(family="Arial", size=12),
            text_color="gray60",
        ).pack()

        target_ws_id = ws.id
        target_subpath = self._current_subpath

        def fetch_assets():
            try:
                manager = WorkspaceManagerUseCase()
                # Chamada pesada de rede em segundo plano
                assets = manager.get_workspace_assets_sync_status(target_ws_id, AppState.drive_service, target_subpath)

                def render_results():
                    # Evitar race condition caso o usuário tenha trocado de workspace/pasta
                    if not self.winfo_exists() or self._selected_workspace_id != target_ws_id or self._current_subpath != target_subpath:
                        return
                    
                    loading_frame.destroy()

                    if not assets:
                        ctk.CTkLabel(
                            self._assets_scroll,
                            text="Esta pasta está vazia.\nColoque arquivos na pasta local do projeto ou clique em 'Enviar Asset'.",
                            font=ctk.CTkFont(family="Arial", size=11),
                            text_color="gray50",
                        ).pack(pady=40)
                        return

                    for asset in assets:
                        rel_key = os.path.join(target_subpath, asset.name).replace("\\", "/")
                        is_uploading = rel_key in self._uploading_files

                        status_txt = "SYNCHRONIZED"
                        if is_uploading:
                            status_txt = "Enviando..."
                        elif asset.status.name == "REMOTE_ONLY":
                            status_txt = "Nuvem"
                        elif asset.status.name == "LOCAL_ONLY":
                            status_txt = "Pendente de Envio"

                        is_dir = asset.mime_type == "application/vnd.google-apps.folder"

                        if is_dir:
                            click_cmd = lambda a=asset: self._enter_folder(ws, a.name)
                        else:
                            click_cmd = lambda a=asset: self._manage_file_modal(ws, a)

                        card = FileCard(
                            self._assets_scroll,
                            name=asset.name,
                            mime_type=asset.mime_type or "application/octet-stream",
                            size=asset.formatted_size if not is_dir else None,
                            modified=asset.modified_time,
                            status_text=status_txt,
                            on_click=click_cmd,
                            on_sync=None if is_dir else (lambda a=asset: self._sync_asset_action(ws, a)),
                            on_rename=lambda a=asset: self._rename_item_prompt(ws, a.name),
                            on_delete=lambda a=asset: self._delete_item_confirm(ws, a.name),
                            is_uploading=is_uploading
                        )
                        card.pack(fill="x", padx=4, pady=3)

                self.after(0, render_results)

            except Exception as e:
                def render_error():
                    if not self.winfo_exists() or self._selected_workspace_id != target_ws_id or self._current_subpath != target_subpath:
                        return
                    loading_frame.destroy()
                    ctk.CTkLabel(
                        self._assets_scroll,
                        text=f"❌ Erro ao sincronizar: {str(e)}",
                        font=ctk.CTkFont(family="Arial", size=11),
                        text_color="red",
                    ).pack(pady=40)
                self.after(0, render_error)

        threading.Thread(target=fetch_assets, daemon=True).start()




    def _enter_folder(self, ws, folder_name: str) -> None:
        self._current_subpath = os.path.join(self._current_subpath, folder_name)
        self._refresh_workspace_assets(ws)

    def _go_back_directory(self, ws) -> None:
        self._current_subpath = os.path.dirname(self._current_subpath)
        self._refresh_workspace_assets(ws)

    def _create_folder_prompt(self, ws) -> None:
        from state import AppState
        from use_cases import WorkspaceManagerUseCase
        
        def do_create(name):
            manager = WorkspaceManagerUseCase()
            if manager.create_workspace_folder(ws.id, self._current_subpath, name, AppState.drive_service):
                self._refresh_workspace_assets(ws)
                
        InputDialog(self._parent, title="Criar Pasta", prompt="Nome da nova pasta:", callback=do_create)

    def _manage_folder_modal(self, ws, folder_name: str) -> None:
        modal = ctk.CTkToplevel(self._parent)
        modal.title(f"Pasta: {folder_name}")
        modal.geometry("320x240")
        modal.grab_set()
        modal.resizable(False, False)

        ctk.CTkLabel(modal, text=f"📂 Pasta: {folder_name}", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=16)

        ButtonComponent(
            parent=modal,
            label="📁 Entrar na Pasta",
            size="medium",
            variant="success",
            onClick=lambda: [modal.destroy(), self._enter_folder(ws, folder_name)]
        ).pack(pady=8, fill="x", padx=40)

        ButtonComponent(
            parent=modal,
            label="✏️ Renomear Pasta",
            size="medium",
            variant="primary",
            onClick=lambda: [modal.destroy(), self._rename_item_prompt(ws, folder_name)]
        ).pack(pady=8, fill="x", padx=40)

        ButtonComponent(
            parent=modal,
            label="🗑️ Excluir Pasta",
            size="medium",
            variant="danger",
            onClick=lambda: [modal.destroy(), self._delete_item_confirm(ws, folder_name)]
        ).pack(pady=8, fill="x", padx=40)

    def _manage_file_modal(self, ws, asset) -> None:
        modal = ctk.CTkToplevel(self._parent)
        modal.title(f"Arquivo: {asset.name}")
        modal.geometry("500x480")
        modal.grab_set()

        ctk.CTkLabel(modal, text=f"📄 {asset.name}", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 4))
        ctk.CTkLabel(modal, text=f"Tamanho: {asset.formatted_size}   |   Status: {asset.status.name}   |   Versão: 1.0", font=ctk.CTkFont(size=11), text_color="gray50").pack(pady=2)

        # Preview area
        preview_frame = ctk.CTkFrame(modal, fg_color="#13232c", corner_radius=8, height=180)
        preview_frame.pack(fill="both", expand=True, padx=20, pady=12)

        preview_lbl = ctk.CTkLabel(preview_frame, text="Sem visualização disponível", text_color="gray60")
        preview_lbl.pack(pady=60)

        # Carregar texto de visualização se aplicável
        if asset.local_path and os.path.exists(asset.local_path):
            ext = os.path.splitext(asset.name)[1].lower()
            if ext in [".txt", ".json", ".md", ".py"]:
                try:
                    with open(asset.local_path, "r", encoding="utf-8") as f:
                        text_content = f.read(1500)
                    preview_lbl.destroy()
                    textbox = ctk.CTkTextbox(preview_frame, fg_color="transparent", text_color="#ffffff")
                    textbox.pack(fill="both", expand=True, padx=8, pady=8)
                    textbox.insert("1.0", text_content)
                    textbox.configure(state="disabled")
                except Exception as ex:
                    print(f"Erro preview texto: {ex}")
            elif ext in [".png", ".jpg", ".jpeg"]:
                try:
                    from PIL import Image, ImageTk
                    # Carregar imagem redimensionada
                    pil_img = Image.open(asset.local_path)
                    pil_img.thumbnail((360, 160))
                    tk_img = ImageTk.PhotoImage(pil_img)
                    
                    preview_lbl.configure(text="", image=tk_img)
                    # Manter referência para evitar garbage collection
                    preview_lbl.image = tk_img
                except Exception as ex:
                    print(f"Erro preview imagem: {ex}")

        # Ações
        actions_row = ctk.CTkFrame(modal, fg_color="transparent")
        actions_row.pack(fill="x", padx=20, pady=(0, 20))

        ButtonComponent(
            parent=actions_row,
            label="✏️ Renomear",
            size="small",
            variant="primary",
            onClick=lambda: [modal.destroy(), self._rename_item_prompt(ws, asset.name)]
        ).pack(side="left", padx=5)

        ButtonComponent(
            parent=actions_row,
            label="📦 Mover",
            size="small",
            variant="secondary",
            onClick=lambda: [modal.destroy(), self._move_item_prompt(ws, asset.name)]
        ).pack(side="left", padx=5)

        ButtonComponent(
            parent=actions_row,
            label="🗑️ Excluir",
            size="small",
            variant="danger",
            onClick=lambda: [modal.destroy(), self._delete_item_confirm(ws, asset.name)]
        ).pack(side="right", padx=5)

    def _rename_item_prompt(self, ws, old_name: str) -> None:
        from state import AppState
        from use_cases import WorkspaceManagerUseCase
        
        def do_rename(new_name):
            manager = WorkspaceManagerUseCase()
            if manager.rename_workspace_item(ws.id, self._current_subpath, old_name, new_name, AppState.drive_service):
                self._refresh_workspace_assets(ws)
                
        InputDialog(self._parent, title="Renomear Item", prompt=f"Renomear '{old_name}' para:", callback=do_rename, initial_value=old_name)

    def _delete_item_confirm(self, ws, name: str) -> None:
        def do_delete():
            from state import AppState
            from use_cases import WorkspaceManagerUseCase
            manager = WorkspaceManagerUseCase()
            if manager.delete_workspace_item(ws.id, self._current_subpath, name, AppState.drive_service):
                self._refresh_workspace_assets(ws)

        ModalDialog(
            self._parent,
            title="Confirmar Exclusão",
            message=f"Deseja excluir permanentemente '{name}' do local e do Drive?",
            on_confirm=do_delete,
            confirm_label="Excluir"
        )

    def _move_item_prompt(self, ws, name: str) -> None:
        from state import AppState
        from use_cases import WorkspaceManagerUseCase
        
        def do_move(dest):
            manager = WorkspaceManagerUseCase()
            if manager.move_workspace_item(ws.id, self._current_subpath, dest, name, AppState.drive_service):
                self._refresh_workspace_assets(ws)

        InputDialog(
            self._parent,
            title="Mover Arquivo",
            prompt="Caminho relativo de destino (deixe vazio para raiz):",
            callback=do_move,
            initial_value=self._current_subpath
        )

    def _sync_asset_action(self, ws, asset) -> None:
        from state import AppState
        from use_cases import WorkspaceManagerUseCase

        if asset.status.name == "SYNCHRONIZED":
            return

        def run():
            manager = WorkspaceManagerUseCase()
            success = manager.sync_asset(
                workspace_id=ws.id,
                asset=asset,
                drive_service=AppState.drive_service,
                author_email=AppState.user_email,
                subpath=self._current_subpath
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

            suggested_path = os.path.join(self._base_dir_var.get(), name)

            from use_cases import WorkspaceManagerUseCase
            manager = WorkspaceManagerUseCase()
            manager.create_workspace(
                name=name,
                description=desc,
                engine=engine,
                owner=AppState.user_email,
                drive_service=AppState.drive_service,
                local_path=suggested_path
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

        from use_cases import WorkspaceManagerUseCase
        manager = WorkspaceManagerUseCase()
        ws = manager.get_workspace_by_id(self._selected_workspace_id)
        if not ws or not ws.local_path:
            return

        src_path = filedialog.askopenfilename(title="Selecionar Asset para Enviar")
        if not src_path:
            return

        filename = os.path.basename(src_path)
        dest_path = os.path.join(ws.local_path, self._current_subpath, filename)

        # 1. Copiar arquivo localmente para a pasta do workspace
        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            ModalDialog(
                self._parent,
                title="Erro Local",
                message=f"Não foi possível copiar o arquivo localmente: {e}",
                cancel_label="Fechar"
            )
            return

        # 2. Adicionar na lista de uploads ativos (caminho relativo)
        rel_key = os.path.join(self._current_subpath, filename).replace("\\", "/")
        self._uploading_files.add(rel_key)

        # Atualizar a UI imediatamente para exibir o card transparente "Enviando..."
        self._refresh_workspace_assets(ws)

        # 3. Fazer upload real no Drive em background e emitir notificação
        def run_upload():
            from state import AppState
            success = manager.upload_and_notify_asset(
                workspace_id=ws.id,
                subpath=self._current_subpath,
                filename=filename,
                local_path=dest_path,
                drive_service=AppState.drive_service,
                author_email=AppState.user_email
            )
            
            # Remover dos uploads ativos
            self._uploading_files.discard(rel_key)
            
            if success:
                self.after(0, lambda: ModalDialog(
                    self._parent,
                    title="Sucesso",
                    message=f"Arquivo '{filename}' copiado e sincronizado com o Drive com sucesso!",
                    cancel_label="Fechar"
                ))
            else:
                self.after(0, lambda: ModalDialog(
                    self._parent,
                    title="Erro de Envio",
                    message=f"O arquivo '{filename}' foi copiado localmente, mas falhou ao enviar ao Drive.",
                    cancel_label="Fechar"
                ))
            # Atualizar a UI para tornar o card sólido/finalizado
            self.after(0, lambda: self._refresh_workspace_assets(ws))

        threading.Thread(target=run_upload, daemon=True).start()


    def _delete_workspace_action(self) -> None:
        if not self._selected_workspace_id:
            return
        
        def do_delete():
            from use_cases import WorkspaceManagerUseCase
            from state import AppState
            import threading

            def run():
                manager = WorkspaceManagerUseCase()
                manager.delete_workspace(self._selected_workspace_id, AppState.drive_service, AppState.user_email)
                self._selected_workspace_id = None
                self.after(0, self._refresh_workspaces)

            threading.Thread(target=run, daemon=True).start()

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
