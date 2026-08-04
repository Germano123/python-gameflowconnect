# GameFlow Connect — Alinhamento Estratégico e Arquitetura DVCS (GFC-DVCS)

> **Data do Alinhamento:** 30 de Julho de 2026
> **Status:** Aprovado para Implementação
> **Versão da Arquitetura:** GFC-DVCS v1.0

Este documento formaliza as decisões de engenharia de software e as mudanças estratégicas acordadas para o reposicionamento do **GameFlow Connect** de uma ferramenta de sincronização e integração simples para um **Sistema de Versionamento Distribuído (DVCS)** autocontido e otimizado para o desenvolvimento de jogos, utilizando o Google Drive como infraestrutura de armazenamento.

---

## 1. Visão Geral das Mudanças Estratégicas

A transição da versão de integração simples (`v2.0.0-alpha`) para a nova arquitetura **GFC-DVCS** baseia-se em cinco decisões estratégicas fundamentais:

### Decisão 1: Endereçamento por Conteúdo (Content-Addressable Storage - CAS)
* **Como era:** Arquivos eram enviados para o Google Drive mantendo seus nomes e localizações físicas (ex: `Assets/Textures/hero.png` local era carregado para `Assets/Textures/hero.png` remoto).
* **Nova Diretriz:** Todo arquivo modificado terá seu hash SHA256 calculado e será armazenado no diretório `.gameflow/objects/[SHA256]` de forma imutável.
* **Justificativa:** Garante a integridade absoluta dos arquivos (verificação de hash), permite a eliminação nativa de duplicidade (deduplicação) e suporta cache local e remoto altamente eficientes. Arquivos antigos nunca são sobrescritos, facilitando reverter versões.

### Decisão 2: Metadados Descentralizados e Autocontidos
* **Como era:** O mapeamento e histórico de alterações dependiam fortemente de tabelas locais em um banco SQLite (`gameflow_local.db`). Se o banco fosse excluído, o rastreamento histórico de versões no Drive seria perdido.
* **Nova Diretriz:** O repositório remoto (a pasta no Google Drive do proprietário) e o repositório local contêm uma pasta oculta `.gameflow/` que armazena toda a árvore de histórico de maneira puramente textual (arquivos JSON para Commits, Branches e Manifestos).
* **Justificativa:** Remove a dependência de bancos de dados centrais ou externos. Cada cópia do projeto é independente e autocontida. O histórico e as ramificações de desenvolvimento podem ser totalmente reconstruídos apenas lendo os dados salvos no Drive.

### Decisão 3: Commits Baseados em DAG e Snapshots Temporários
* **Como era:** Sincronizações ocorriam enviando alterações diretamente na medida em que arquivos eram alterados ou de forma manual em lote simples.
* **Nova Diretriz:** O fluxo de trabalho agora é baseado em commits formais que constituem um grafo acíclico direcionado (DAG), onde cada commit aponta para seu commit pai. Modificações em andamento residem em um "Workspace Snapshot" local com estados bem definidos (`Draft`, `Pending`, `Approved`, `Rejected`, `Merged`), permitindo que administradores e líderes de time aprovem alterações antes que elas façam parte da branch principal.
* **Justificativa:** Suporta o fluxo de trabalho típico de times de desenvolvimento de jogos (Lead Artist aprovando arte, Lead Programmer revisando código/prefabs) antes de integrar no ramo de produção.

### Decisão 4: Controle de Acesso e Concorrência por Locks de Binários
* **Como era:** Conflitos eram detectados após o upload e resolvidos manualmente (substituindo local ou remoto).
* **Nova Diretriz:** Para arquivos pesados ou binários (imagens, malhas 3D, mapas e cenas), o sistema oferece um mecanismo de **Locks** (bloqueios exclusivos temporários) registrados no Drive (`.gameflow/locks/[asset_uuid].json`).
* **Justificativa:** Arquivos binários não podem ser mesclados de forma automática (diferente de código-fonte). O bloqueio de arquivos na edição evita conflitos dispendiosos de retrabalho.

### Decisão 5: Novo Papel do Banco de Dados Local
* **Como era:** Fonte de verdade operacional para versionamento e cache de assets.
* **Nova Diretriz:** O banco local SQLite passa a ser tratado estritamente como um **índice de performance** e cache de visualização rápida da UI.
* **Justificativa:** Caso o banco de dados SQLite local seja corrompido ou apagado, o sistema executa um algoritmo de reconstrução que relê a estrutura `.gameflow/` no disco e no Drive, recriando o banco SQLite local do zero sem nenhuma perda de informação histórica do projeto.

---

## 2. Nova Estrutura de Diretórios do Projeto (.gameflow)

Todo projeto GameFlow Connect terá a seguinte estrutura interna e remota:

```text
[Diretório do Projeto]/
├── Assets/ (e outros diretórios da engine)
└── .gameflow/
    ├── manifests/
    │   └── project.json       # Estado atual, branches, cabeças e usuários
    ├── objects/
    │   ├── a9/1f2283cb7...    # Conteúdo dos arquivos (divididos em subdiretórios)
    │   └── ...
    ├── commits/
    │   ├── c12345ab.json      # Metadados do Commit (JSON)
    │   └── ...
    ├── branches/
    │   ├── main.json          # Ponteiro para o commit de cabeça da branch main
    │   └── develop.json       # Ponteiro para a branch develop
    ├── snapshots/
    │   ├── snap_user123.json  # Snapshots de trabalho em aprovação
    │   └── ...
    ├── users/
    │   └── registry.json      # Permissões e colaboradores do projeto
    └── locks/
        └── lock_asset456.json # Arquivos de Lock de binários ativos
```

---

## 3. Especificação das Estruturas de Dados (Esboço JSON)

### Commit (`.gameflow/commits/[commit_hash].json`)
```json
{
  "hash": "c12345ab890ef...",
  "parents": ["a98765bcde..."],
  "author": "developer@email.com",
  "timestamp": "2026-07-30T23:30:00Z",
  "message": "Atualiza script de movimento do player e modelo 3D",
  "changes": [
    {
      "asset_id": "uuid-do-script-de-movimento",
      "logical_path": "Scripts/PlayerController.cs",
      "action": "MODIFY",
      "object_hash": "b81cd3f9a72...",
      "version": 4
    },
    {
      "asset_id": "uuid-do-mesh-fbx",
      "logical_path": "Models/Player.fbx",
      "action": "MODIFY",
      "object_hash": "f193aa82cbd...",
      "version": 2
    }
  ]
}
```

### Lock (`.gameflow/locks/[asset_uuid].json`)
```json
{
  "asset_id": "uuid-do-mesh-fbx",
  "owner": "artist@email.com",
  "locked_at": "2026-07-30T21:00:00Z",
  "duration_seconds": 7200,
  "expires_at": "2026-07-30T23:00:00Z"
}
```

---

## 4. Plano de Transição Arquitetônica

1. **Refatoração de Entidades:** Adaptar `Asset` e `Workspace` no domínio do sistema para incorporar UUIDs fixos, hashes de conteúdo e cabeças de branches.
2. **Evolução do Schema SQLite:** Atualizar `database.py` para refletir tabelas de `commits`, `branches`, `locks` e `snapshots` como índices locais de performance.
3. **Criação da Sync Engine Incremental:** Desenvolver algoritmos de upload/download de blobs com base no hash SHA256 na pasta `.gameflow/objects/` do Google Drive.
4. **Rotina de Reconstrução:** Implementar o caso de uso `ReconstructWorkspace` que lê arquivos de commits JSON remotos para regenerar o SQLite local.
