# Cronograma de Desenvolvimento

## Atividades

### Etapa 1 - Configuração de ambiente
- [X] Instalar Python
- [X] Instalar TKinter
- [X] Instalar Git
- [X] Configurar repositório inicial no GitHub
- [X] Pesquisar e definir as melhores práticas para integração com Google Drive
- [X] Pesquisar e definir as melhores práticas para integração com GitHub

### Etapa 2 - Integração com Google Drive
- [X] Investigar APIs disponíveis para autenticação e manipulação de arquivos
- [X] Autenticação OAuth para contas do Google
- [X] Interface de usuário para conectar e desconectar contas
- [X] Implementar o upload e download de arquivos para/da conta vinculada do Google Drive

### Etapa 3 - Integração com GitHub e Git Versioning
- [X] Autenticação via token (PAT)
- [X] Interface para conectar e visualizar repositórios
- [X] Integrar o sistema de versionamento Git no projeto
- [ ] Permitir commits avançados, criação de branches, e merges diretamente na UI

### Etapa 4 - Implementação da Interface do Usuário (UI)
- [X] Estruturar design patterns e boas práticas com TKinter (Atomic Design & Clean Architecture)
- [X] Criar a estrutura inicial da interface do usuário usando TKinter / CustomTkinter
- [X] Design básico para as guias (Google Drive, GitHub, Git Local, Configurações)
- [X] Adicionar elementos de UI para upload/download e sincronização de arquivos (`FileCard`, Modais)

### Etapa 5 - Melhorar a experiência do usuário (UX) ao gerenciar assets
- [X] Sincronização de alterações de mídia entre membros da equipe (Fase 1: Imagens)
- [ ] Sincronização avançada para Documentos (Fase 2) e Modelos 3D (Fase 3)
- [ ] Adicionar funcionalidade de visualização (preview) de assets no próprio tool
- [X] Suporte a temas (Dark/Light mode via CustomTkinter) e Modo Demo

### Etapa 6 - Melhorar funções de gerenciamento
- [ ] Implementar um sistema de rastreamento de tarefas e problemas
- [ ] Adicionar uma guia de tarefas e problemas à interface
- [ ] Desenvolver um sistema de notificação para manter a equipe informada
- [X] Gerenciar diferentes tipos de arquivos do projeto (`AssetType`: Image, Document, Model 3D, Misc)

### Etapa 7 - Testes de integração e primeira versão
- [X] Realizar testes de integração e unidade (`tests/test_clean_architecture.py` & `tests/test_drive_service.py`)
- [X] Identificar e corrigir bugs de conexão OAuth e erros de runtime (`invalid_grant`, `credentials.json`)
- [X] Refinar a interface do usuário com base nos feedbacks dos testes
- [X] Documentar o código-fonte
- [X] Incluir instruções claras para instalação, configuração do Google Cloud Console e uso
- [ ] Preparar o pacote de entrega e compilação de executável final

---

*Nota: Este cronograma é mantido e atualizado conforme o progresso do desenvolvimento.*
