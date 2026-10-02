# Manual do Usuário — Aurora Elo

> Versão: Sprint 9 | Atualizado em: 2026-10-02 | Branch: `gemini`

---

## Sumário

1. [Acesso ao Sistema](#1-acesso-ao-sistema)
2. [Área Administrativa da Clínica](#2-área-administrativa-da-clínica)
3. [Dashboard e Workspace](#3-dashboard-e-workspace)
4. [Pacientes e Prontuário](#4-pacientes-e-prontuário)
5. [Agenda e Agendamento](#5-agenda-e-agendamento)
6. [Módulo Concierge (Pós-Alta)](#6-módulo-concierge-pós-alta)
7. [Psiquiatria Clínica](#7-psiquiatria-clínica)
8. [Farmácia e Operações Clínicas](#8-farmácia-e-operações-clínicas)
9. [App Pós-Alta do Paciente (Mobile)](#9-app-pós-alta-do-paciente-mobile)
10. [Consentimentos e LGPD](#10-consentimentos-e-lgpd)
11. [Painel Master (Proprietário do SaaS)](#11-painel-master-proprietário-do-saas)
12. [Instalação como App (PWA)](#12-instalação-como-app-pwa)

---

## 1. Acesso ao Sistema

### 1.1 Login
- **URL:** `https://auroraelo.rgnsystems.com.br/master/login/` (master) ou `/psiquiatria/login/` (clínica)
- **Credenciais:** fornecidas pelo administrador da clínica
- **MFA:** compatível com autenticadores TOTP (Google Authenticator, Authy)

### 1.2 Perfis de Acesso (RBAC)
O sistema adapta automaticamente a interface de acordo com o perfil:

| Perfil | Interfaces disponíveis |
|--------|------------------------|
| **Administrador de Clínica** | Dashboard geral, pacientes, agenda, concierge, farmácia, faturamento, equipe |
| **Psiquiatra** | Dashboard clínico, prontuário, prescrições, anamnese com IA |
| **Psicólogo** | Prontuário (anotações isoladas), diário compartilhado, metas |
| **Enfermagem / Monitor** | Rotinas, checkins, agenda, concierge |
| **Farmácia** | Estoque, dispensação, travas de medicação SOS |
| **Financeiro** | Faturamento, pagamentos, fechamento de conta |

> **Isolamento de dados:** Anotações do psicólogo são invisíveis para outras áreas (CFP/CRP-PE).

---

## 2. Área Administrativa da Clínica

### 2.1 Cadastros básicos
- **Setores:** `Administração > Setores` — crie setores como "Enfermaria", "Psicologia", "Farmácia"
- **Funções:** `Administração > Funções` — vincule funções a setores e defina permissões RBAC
- **Profissionais:** `Administração > Equipe` — cadastre CPF, CRM/CRP, e-mail institucional e função

### 2.2 Leitos e Internações
- **Cadastro de leitos:** `Administração > Leitos` — informe nome/número, setor e capacidade
- **Alocação:** realizada pela administração ao registrar uma internação
- **Regras de visita:** configuráveis em `Administração > Configurações > Comunicação` (padrão: ligação 7º dia, ligação 15º dia, visita 15º dia)

### 2.3 Cadastro de Pacientes
- **Pela administração:** `Pacientes > Novo paciente` — preencha dados pessoais, plano de saúde e responsável legal
- **Dados sensíveis:** criptografados em repouso (AES-256 via `django-cryptography`)

---

## 3. Dashboard e Workspace

O **Workspace** é a área de trabalho principal. Ao fazer login, o sistema redireciona para o dashboard correspondente ao perfil.

### 3.1 Navegação
- **Barra lateral:** acesso aos módulos autorizados para o perfil logado
- **Seletor de clínica:** no topo, permite alternar entre clínicas (para profissionais com atuação em múltiplas unidades)
- **Preferências de layout:** `Workspace > Preferências` — escolha sidebar compacto ou expandido

### 3.2 Indicadores do Dashboard
- **Pacientes internados hoje**
- **Consultas agendadas (próximas 24h)**
- **Alertas de crise ativos**
- **Pendências de consentimento**

---

## 4. Pacientes e Prontuário

### 4.1 Prontuário Eletrônico do Paciente (PEP)
- **Acesso:** `Pacientes > [nome do paciente] > Prontuário`
- **Histórico de versões:** cada alteração registra o usuário, data/hora e conteúdo anterior (trilha Anvisa)
- **Assinatura eletrônica:** prescrições e evoluções exigem confirmação do profissional (PIN ou senha)

### 4.2 Anamnese com IA
- **Acesso:** no prontuário, clique em "Sugestão de Anamnese"
- **Modelo:** GPT-4o (OpenAI) — sugestões não substituem o julgamento clínico
- **Privacidade:** dados anônimos enviados à API; prontuário completo nunca trafega para OpenAI

### 4.3 Diário do Paciente
- O paciente registra entradas pelo App Pós-Alta
- O profissional autorizado vê o diário em `Pacientes > [paciente] > Diário`
- **Visibilidade:** controlada pelo próprio paciente (entrada por entrada)

---

## 5. Agenda e Agendamento

### 5.1 Criar consulta
1. Acesse `Agenda > Nova consulta`
2. Selecione paciente, profissional e horário disponível
3. Confirme — o paciente recebe notificação via app

### 5.2 Calendário
- Visualize por **dia**, **semana** ou **mês**
- Cores indicam o status: 🟢 confirmada, 🟡 pendente, 🔴 cancelada

### 5.3 Gerenciar consulta existente
- **Reagendar:** clique na consulta > "Reagendar"
- **Cancelar:** informe o motivo (registrado na trilha de auditoria)
- **Completar:** marque como realizada para fechar o ciclo

---

## 6. Módulo Concierge (Pós-Alta)

O **Concierge** gerencia o acompanhamento do paciente após a alta hospitalar, controlando o contato com a família e as atividades de suporte.

### 6.1 Dashboard do Concierge
- **Acesso:** `Concierge > Dashboard`
- **Métricas:** pacientes em acompanhamento ativo, ligações pendentes, visitas programadas

### 6.2 Régua de Contato
A régua padrão (configurável por clínica):
- **7º dia:** 1ª ligação de acompanhamento
- **15º dia:** 2ª ligação + visita presencial agendada

Para ajustar: `Administração > Configurações > Régua de Comunicação`

### 6.3 Registrar Contato
1. `Concierge > Paciente > [nome]`
2. Clique em "Registrar contato"
3. Preencha: tipo (ligação/visita), responsável, observações e próxima ação
4. O registro é auditado e imutável

### 6.4 Solicitações do Paciente
- Pedidos feitos pelo paciente à família (itens pessoais, etc.) são registrados em `Concierge > Solicitações`
- Status: **Pendente → Em andamento → Entregue**

---

## 7. Psiquiatria Clínica

### 7.1 Prescrições
- **Nova prescrição:** `Psiquiatria > Prescrições > Nova`
- **Medicação SOS:** requer trava adicional (confirmação de PIN do prescritor)
- **Histórico:** imutável, com assinatura eletrônica

### 7.2 12 Passos (Adictologia)
- Módulo para acompanhamento de programas de 12 Passos
- Registro de progresso, rascunhos e consolidação de etapas

### 7.3 Anamnese Estruturada
- Formulários clínicos pré-configurados com campos obrigatórios por especialidade
- Integração com sugestão de IA (GPT-4o)

---

## 8. Farmácia e Operações Clínicas

> **Isolamento total:** a interface de Farmácia é visível **apenas** para o perfil `farmácia`.

### 8.1 Estoque
- `Farmácia > Estoque` — cadastre medicamentos, lotes e validades
- **Alertas automáticos:** estoque abaixo do mínimo e medicamentos próximos do vencimento

### 8.2 Dispensação
- Vincule a dispensação à prescrição do médico
- Registro auditado com quantidade, lote e profissional responsável

### 8.3 Autorização de Movimentações
- Aprovação em dois níveis para psicotrópicos (farmacêutico + médico)

---

## 9. App Pós-Alta do Paciente (Mobile)

O **App Pós-Alta** é acessível pelo paciente via smartphone após a alta.

### 9.1 Ativação da Conta
1. A clínica cadastra o paciente e envia o **link de ativação** por e-mail
2. O paciente clica no link, define sua senha e ativa a conta
3. Login com e-mail + senha (token Bearer com refresh automático)

### 9.2 Funcionalidades do App
| Seção | O que o paciente faz |
|-------|---------------------|
| **Agenda** | Ver e solicitar consultas, cancelar com justificativa |
| **Diário** | Registrar reflexões; controla quem pode ler |
| **Metas** | Acompanhar metas definidas com o terapeuta |
| **Medicamentos** | Ver prescrições e registrar doses tomadas |
| **Recuperação** | Contador de sobriedade, registro de fissuras |
| **Rede de Apoio** | Contatos de emergência e profissionais de referência |
| **Conteúdos** | Artigos e vídeos recomendados pela equipe |
| **Check-in** | Responder formulários de bem-estar diários |

### 9.3 Segurança
- Autenticação Bearer com JWT rotativo (refresh a cada 24h)
- Sessões gerenciadas: o paciente pode revogar dispositivos em `Conta > Sessões`
- Dados trafegam exclusivamente em HTTPS/TLS 1.3

---

## 10. Consentimentos e LGPD

### 10.1 Gestão de Consentimentos
- `Configurações > Consentimentos` — cadastre documentos (TCLE, LGPD, uso de imagem)
- Pacientes assinam pelo App Pós-Alta ou em tablet na recepção
- **Rastreabilidade:** data, IP, dispositivo e versão do documento registrados

### 10.2 Solicitações de Privacidade (DSAR)
- Paciente solicita acesso, correção ou exclusão de dados pelo app
- Clínica gerencia em `LGPD > Solicitações` com prazo de 15 dias (ANPD)

### 10.3 Revogação de Consentimento
- Notificações de revogação pendente aparecem no dashboard do administrador
- Prazo e responsável são rastreados automaticamente

---

## 11. Painel Master (Proprietário do SaaS)

> Acesso exclusivo para a equipe Aurora Elo.

- **URL:** `/master/`
- Gestão de clínicas cadastradas, planos de assinatura e faturamento
- Bloqueio de acesso por inadimplência (HTTP 402 nas rotas da clínica)
- Visão consolidada de uso e métricas de saúde do sistema

---

## 12. Instalação como App (PWA)

O Aurora Elo pode ser instalado como aplicativo no dispositivo da equipe clínica (Android, iOS, desktop).

### 12.1 Android / Chrome
1. Acesse o sistema pelo Chrome
2. Toque no menu (⋮) > **"Adicionar à tela inicial"**
3. Confirme — o ícone Aurora Elo aparecerá na tela inicial

### 12.2 iOS / Safari
1. Acesse pelo Safari
2. Toque em **Compartilhar** (□↑) > **"Adicionar à Tela de Início"**
3. Confirme o nome e toque em **Adicionar**

### 12.3 Desktop (Chrome/Edge)
1. Clique no ícone de instalação (⊕) na barra de endereços
2. Clique em **"Instalar"**

> **Funcionamento offline:** páginas visitadas recentemente ficam disponíveis mesmo sem internet. Ao voltar à conectividade, os dados são sincronizados automaticamente.

---

*Aurora Elo — Plataforma SaaS de Saúde Mental | Versão Sprint 9*
*Documentação gerada em 2026-10-02 | Suporte: suporte@auroraelo.com.br*
