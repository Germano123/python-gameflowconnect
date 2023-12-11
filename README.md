# GameFlowConnect
**Uma Ferramenta de Colaboração para Artistas, Programadores e Designers de Jogos**

O GameFlowConnect é uma ferramenta projetada para facilitar a colaboração efetiva entre artistas, programadores e designers de jogos, fornecendo uma plataforma centralizada para a troca e envio de assets dentro de um projeto. O sistema utiliza o core em Python e a biblioteca de UI TKinter para uma experiência amigável e intuitiva.

## Os Problemas
O uso de diversos assets em um projeto de desenvolvimento de jogos pode ser constatemente repetitivo. Alterar pequenos detalhes e exportar esses arquivos pode ser uma tarefa repetitiva e monótona além de ser um peso extra para artistas que não tem experiência com ferramentas de versionamento.

Conflitos de Versionamento

> Problema: Em equipes grandes de desenvolvimento de jogos, vários membros podem trabalhar em diferentes partes do jogo simultaneamente. Isso pode resultar em conflitos durante o processo de versionamento, especialmente ao mesclar alterações feitas por diferentes desenvolvedores. Resolver esses conflitos manualmente pode ser demorado e propenso a erros.

Gestão e Duplicação de Assets

> Problema: Coordenar a criação e distribuição de ativos do jogo em uma equipe grande pode resultar em arquivos duplicados, convenções de nomenclatura inconsistentes e dificuldades para rastrear as últimas versões. Isso pode causar confusão e prejudicar a eficiência geral do processo de desenvolvimento.

Falhas na Comunicação

> Problema: À medida que as equipes crescem, a comunicação eficaz torna-se mais desafiadora. Membros da equipe podem perder atualizações importantes, alterações ou discussões, levando a mal-entendidos, esforços duplicados e atrasos nos prazos do projeto.

Desafios de Integração

> Problema: Integrar diferentes componentes desenvolvidos por vários membros da equipe pode ser complexo, especialmente em equipes grandes onde o trabalho especializado é distribuído. Garantir que todos os elementos do jogo funcionem de maneira coesa e sem bugs pode se tornar um desafio significativo.

Segurança e Controle de Acesso

> Problema: Equipes grandes podem incluir membros com diferentes funções e responsabilidades. Garantir que informações sensíveis, como credenciais de acesso, chaves de API ou ativos proprietários, estejam seguras e acessíveis apenas por membros autorizados da equipe é crucial. A falha em gerenciar o controle de acesso efetivamente pode resultar em violações de dados ou modificações não autorizadas no projeto.

## Soluções
Este sistema traz a possibilidade de ser um fácil acesso para artistas poderem atuar controlando versões

## Funcionalidades Principais
1. Integração com o Google Drive

A ferramenta permite que os usuários conectem suas contas do Google Drive, permitindo o armazenamento fácil e seguro dos ativos do projeto. Essa integração agiliza o processo de compartilhamento e acesso a arquivos no ambiente colaborativo.

2. Integração do repositório GitHub

A ferramenta oferece suporte à integração com repositórios GitHub, permitindo controle de versão eficiente e colaboração entre os membros da equipe. Os desenvolvedores podem facilmente enviar e receber alterações diretamente da ferramenta, garantindo um fluxo de trabalho tranquilo.

3. Versionamento do Git

Por padrão, o sistema utiliza Git para controle de versão dos arquivos do projeto. Isso garante que as alterações feitas por diferentes membros da equipe sejam rastreadas e o histórico do projeto seja mantido. Os usuários podem confirmar alterações, criar ramificações e gerenciar mesclagens diretamente por meio da ferramenta.

4. UI amigável

A interface gráfica do usuário (GUI) é desenvolvida utilizando a biblioteca TKinter, proporcionando uma experiência intuitiva e fácil de usar. O design se concentra na simplicidade e eficiência para aprimorar o processo colaborativo geral.

## Funcionalidades secundárias
1. Colaboração em tempo real

Permita a edição e visualização simultânea de arquivos de projeto por vários membros da equipe em tempo real, promovendo colaboração e feedback imediatos.

2. Pré-visualização e visualização de ativos

Implemente um recurso para visualizar e visualizar ativos do jogo diretamente na ferramenta, permitindo que os membros da equipe inspecionem gráficos, modelos e outras mídias sem a necessidade de aplicativos externos.

3. Rastreador de tarefas e problemas

Integre um sistema de rastreamento de tarefas e problemas para ajudar os membros da equipe a atribuir, rastrear e gerenciar tarefas dentro da ferramenta. Esse recurso pode agilizar o gerenciamento de projetos e melhorar a comunicação entre os membros da equipe.

4. Sistema de Notificação

Desenvolva um sistema de notificação que alerte os usuários sobre alterações feitas por colaboradores, novas tarefas atribuídas ou atualizações importantes do projeto. Isso melhora a comunicação e mantém todos informados sobre o andamento do projeto.

5. Modo offline e sincronização

Implemente um modo offline que permita aos usuários trabalhar no projeto sem conexão com a internet. As alterações feitas off-line devem ser sincronizadas automaticamente com a nuvem (Google Drive) e o repositório (GitHub) assim que a conexão com a Internet for restaurada, garantindo uma colaboração perfeita em vários ambientes.

## Requisitos
- Python 3.6 ou superior
- Biblioteca TKinter
- Git instalado no sistema
- Conta no Google Drive (para integração)
- Conta no GitHub (para integração)

## Instalação
Clone o repositório do GameFlowConnect:
```bash
git clone https://github.com/seu-usuario/GameFlowConnect.git
```

Instale as dependências:
```bash
pip install -r requirements.txt
Configuração
Execute o arquivo config.py para configurar suas credenciais do Google Drive e do GitHub.
```

Siga as instruções para autenticação e autorização.

Uso
Execute o aplicativo

```bash
Copy code
python main.py
Faça login com suas credenciais do Google Drive e do GitHub.
```

Navegue pelos recursos intuitivos para compartilhar, visualizar e controlar versões de assets.

## Identidade visual
As cores escolhidas para este projeto consistem em:
<div style="display: flex; justify-content: center; align-items: center; height: 100px">
    <div style="display: flex; justify-content: center; align-items: center; color: white; background-color: #1e3743; width: 180px; height: 100%; margin: 5px; border-radius: 23px"><p>Primária: #1e3743</p></div>
    <div style="display: flex; justify-content: center; align-items: center; color: white; background-color: #1e3760; width: 180px; height: 100%; margin: 5px; border-radius: 23px"><p>Secundária: #1e3760</p></div>
    <div style="display: flex; justify-content: center; align-items: center; color: white; background-color: #00aa00; width: 180px; height: 100%; margin: 5px; border-radius: 23px"><p>Terciária: #00aa00</p></div>
</div>

## Contribuições
Contribuições são bem-vindas! Por favor, consulte CONTRIBUTING.md para obter detalhes sobre como contribuir para o projeto.
