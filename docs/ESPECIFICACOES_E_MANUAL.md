# Manual do Usuário e Especificação Técnica (Anvisa) - Aurora Elo

## 1. Especificação Funcional e Conformidade (Anvisa & CFP)
Este documento detalha o cumprimento das exigências regulatórias pela plataforma Aurora Elo.

### 1.1 Rastreabilidade e Auditoria
O sistema Aurora Elo utiliza a biblioteca `django-simple-history` acoplada aos modelos fundamentais do Prontuário Eletrônico do Paciente (PEP). 
- **Log de Ações**: Toda criação, alteração ou exclusão de um registro gera uma entrada na tabela de histórico contendo: ID do usuário responsável, endereço IP, data e hora da modificação e o estado anterior dos dados.
- **Assinatura Eletrônica**: Os registros finalizados não podem ser alterados. Apenas adendos (retificações) podem ser incluídos, com data/hora e assinatura do novo registro, de acordo com as resoluções vigentes da Anvisa para PEP (Prontuário Eletrônico do Paciente).

### 1.2 Privacidade e Sigilo Profissional (CFP)
- **Isolamento Psicológico**: As evoluções inseridas por profissionais com o papel `psychologist` (Psicologia) ficam restritas ao próprio profissional ou ao coordenador técnico do mesmo setor. O sistema utiliza criptografia em repouso (`django-cryptography`) nas colunas do banco de dados que contêm as notas psicoterápicas, impedindo o acesso por administradores de banco de dados ou médicos/psiquiatras (`psychiatrist`).
- **Anonimização**: Dados sensíveis em ambientes não-produção são ofuscados.

## 2. Especificação Técnica
### 2.1 Arquitetura Backend
- **Linguagem / Framework**: Python 3.12, Django 5+, e Django Ninja para a construção robusta da API RESTful.
- **Multitenancy**: Gerenciamento de inquilinos isolados por schemas do PostgreSQL.
- **Autenticação**: Padrão JWT (Bearer Tokens) sem estado para aplicativos móveis, com mecanismo rigoroso de expiração e rotas protegidas (`/api/v1/mobile/`).
- **Filas e Assincronismo**: Celery / Redis para envio de emails, agendamento de tarefas e backups diários automatizados.

### 2.2 Rotina de Backup de Segurança
O sistema provê o comando de gerência `backup_to_drive`, orquestrado pelo Celery Beat (`core.tasks.daily_backup`).
O fluxo é executado diariamente:
1. `pg_dump` do banco de dados relacional.
2. Compactação nativa (`gzip`).
3. Criptografia Simétrica da ISO/Arquivo final utilizando `cryptography.fernet` baseada em chave AES (`BACKUP_ENCRYPTION_KEY`).
4. Upload seguro via HTTPS para o Google Drive Corporativo, gerenciado por credenciais do Google Cloud IAM Service Account.

## 3. Manual Básico do Usuário (Mobile Pós-Alta)
**Para o Paciente**:
1. **Acesso**: Após o recebimento da notificação de "Alta e Acompanhamento", clique no link recebido no seu E-mail ou SMS.
2. **Login Seguro**: O aplicativo Aurora Elo (Web PWA) será aberto. Você deverá digitar seu Nome, Sobrenome e o PIN Seguro de 6 dígitos que foi enviado no email.
3. **Painel de Acompanhamento (Dashboard)**: Após autenticado, seu acompanhamento começa.
4. **Funcionalidades**:
   - **Próximos Eventos**: Verifique a data e o horário da sua próxima avaliação (presencial ou online).
   - **Concierge**: Entre em contato imediatamente com o plantão de urgência da clínica que acompanhou o seu processo de saúde, tudo através da aba "Concierge".
   - **Perfil**: Revise as informações vinculadas e gerencie a expiração da sua sessão a qualquer momento clicando em "Sair da Conta".
