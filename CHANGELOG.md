# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0-alpha] - 2026-07-25

Esta versão alfa marca a transição da arquitetura original baseada em projetos locais isolados para a nova arquitetura **descentralizada via Workspaces**, onde o **Google Drive** funciona como fonte de verdade compartilhada de metadados e arquivos (sem dependência de servidor próprio), e o **SQLite local** gerencia o cache rápido.

### Adicionado
- **Automação do Build no Windows**: Script `build_exe.py` na raiz do projeto para empacotar o aplicativo nativamente usando o PyInstaller de forma automatizada e limpa.
- **Instalador Completo do Windows**: Script de configuração `GameFlowConnect.iss` para o Inno Setup Compiler para compilar os binários em um arquivo de instalação executável (`setup.exe`) com atalhos de Desktop e Menu Iniciar.
- **Upload Real de Arquivos com Pré-visualização Transparente**: Ao enviar um arquivo pelo diálogo, ele é fisicamente copiado para a pasta local e enviado ao Drive via thread em background. O card na UI fica semi-transparente com status `[Enviando...]` até a conclusão, tornando-se sólido logo em seguida.
- **Navegação Direta de Pastas (Sem Modal)**: Clicar ou selecionar uma pasta (📁) agora navega diretamente para dentro dela, em vez de exigir confirmação por modal pop-up.
- **Exclusão de Workspaces Persistente**: Tabela `ignored_workspaces` no SQLite local para registrar IDs de projetos excluídos, impedindo que a busca em background os redescubra e recrie automaticamente no próximo carregamento.
- **Gerenciamento de Workspaces e Badges de Equipe**:
  - Tags visuais coloridas: `Proprietário` (verde) e `Convidado` (amarelo) nos cartões de Workspaces e Dashboard.
  - Vínculo automático e persistente com o diretório base configurado pelo usuário.
- **Criação e Sincronização Automática**: Criação automática de pastas e subpastas de arquivos manifestos locais (`.gameflow/manifest.json` e `.gameflow/config.json`) ao aceitar ou descobrir workspaces compartilhados.
- **Campo de Diretório Base Local**: Inserção de campo editável na tela de Workspaces sugerindo `~/Documents/GameFlow` como a raiz padrão de projetos do usuário.

### Corrigido
- **Varredura de Compartilhados**: Correção na busca de manifestos compartilhados por herança de permissões no Google Drive, buscando por `"name = 'manifest.json' and trashed = false"`.
- **Prevenção de Cliques em FileCard**: Correção na propagação de cliques dos botões de ação rápidos (Rename, Delete) no CustomTkinter, evitando disparar cliques gerais do corpo do card.
- **Estado Ativo no SideMenu**: Correção no destaque da tela ativa no menu de navegação lateral durante a transição pelo roteador geral.
- **Segurança no Repositório (.gitignore)**: Atualização do `.gitignore` para ignorar o banco de teste `data_test/`, os arquivos de spec do PyInstaller (`*.spec`), e o diretório de saída do instalador (`output/`).

### Removido
- Removido o rodapé e a opção de "Modo Demo" na página de login e home.
- Removida a rota de criação de contas offline obsoleta (`RegisterPage`).
- Removidos diretórios residuais e temporários (`GameProject` e `GameProjects`) do repositório raiz do projeto.

---

[2.0.0-alpha]: https://github.com/Germano123/python-gameflowconnect/releases/tag/v2.0.0-alpha
