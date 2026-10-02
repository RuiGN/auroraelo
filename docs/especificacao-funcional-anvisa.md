# Especificação Funcional — Aurora Elo
## Conformidade Regulatória (Anvisa / LGPD / CFP)

> **Classificação:** Documento Técnico Interno  
> **Versão:** Sprint 9 | 2026-10-02  
> **Responsável técnico:** Aurora Elo SaaS  
> **Aplicabilidade:** RDC Anvisa nº 63/2011, Lei 13.709/2018 (LGPD), CFP Resolução 11/2018

---

## 1. Identificação do Sistema

| Campo | Valor |
|-------|-------|
| **Nome do Software** | Aurora Elo |
| **Natureza** | SaaS Multitenant — Gestão de Comunidades Terapêuticas e Clínicas Psiquiátricas |
| **Arquitetura** | Python 3.14 / Django 5 / PostgreSQL 17 / Redis 8 |
| **Ambiente de produção** | Docker (VPS Azure), Cloudflare Tunnel (TLS 1.3) |
| **Versão atual** | Sprint 9, commit `4dd91d3` |

---

## 2. Trilha de Auditoria (RDC Anvisa nº 63/2011)

### 2.1 Rastreabilidade de Prontuário
Toda alteração em registros clínicos é auditada com:
- **Quem:** `user_id` + `username` do usuário autenticado
- **Quando:** timestamp UTC com precisão de milissegundos
- **O quê:** campo alterado, valor anterior e valor novo (diff)
- **Como:** endereço IP e `user_agent` do cliente

**Implementação:** `django-simple-history` aplicado a todos os modelos de prontuário, prescrição, anamnese e evolução clínica.

```python
# Exemplo: modelos com auditoria Anvisa
class MedicalRecord(models.Model):
    history = HistoricalRecords()  # django-simple-history

class Prescription(models.Model):
    history = HistoricalRecords()
```

### 2.2 Imutabilidade de Registros
- Registros clínicos **não podem ser deletados** — apenas desativados com registro de motivo
- Alterações geram nova versão; a versão anterior permanece acessível
- Exclusão física bloqueada por `ProtectedError` no ORM

### 2.3 Assinatura Eletrônica
- Prescrições e evoluções médicas exigem confirmação por PIN ou senha do profissional
- Hash SHA-256 do conteúdo + timestamp + user_id armazenado como "assinatura"

---

## 3. Criptografia de Dados Sensíveis

### 3.1 Em Repouso
- **Campos de anotação psicoterápica:** criptografados com `django-cryptography` (AES-256-GCM)
- **Campos de identificação sensível:** CPF, RG, número de convênio
- **Chave de criptografia:** gerenciada via variável de ambiente `FIELD_ENCRYPTION_KEY` (nunca em código)

### 3.2 Em Trânsito
- TLS 1.3 obrigatório (`SECURE_SSL_REDIRECT = True` em produção)
- HSTS habilitado com `max-age=31536000; includeSubDomains`
- API mobile via Cloudflare Tunnel (certificado gerenciado automaticamente)

### 3.3 Backup
- `pg_dump` completo executado diariamente via Celery Beat
- Arquivo comprimido (gzip) e criptografado (AES-256) antes do upload
- Upload automático para Google Drive corporativo via Service Account
- Retenção: 30 dias (configurável)

---

## 4. Isolamento de Dados Psicoterapêuticos (CFP Resolução 11/2018)

### 4.1 Anotações do Psicólogo
- Armazenadas em tabela isolada com criptografia de campo
- Acesso restrito ao grupo Django `psicologia`
- **Invisíveis** para: médicos, enfermagem, administração, farmácia
- Log de acesso registrado mesmo para leituras

### 4.2 Controle de Acesso por Role
```
psicologia:
  - Ler/escrever anotações psicoterapêuticas próprias
  - Ver diário do paciente (se consentido)

psiquiatria:
  - Ler/escrever prontuário clínico
  - NÃO pode ver anotações psicoterapêuticas

farmacia:
  - Ver prescrições (somente)
  - NÃO pode ver prontuário clínico
```

---

## 5. Gestão de Consentimentos (LGPD — Art. 7º, 9º, 18º)

### 5.1 Coleta e Registro de Consentimento
- Documento de consentimento (TCLE, Política de Privacidade, Uso de Imagem) cadastrado com versão e data de vigência
- Paciente assina digitalmente pelo App Pós-Alta ou em tablet na recepção
- Registro inclui: `document_id`, `version`, `user_id`, `timestamp`, `ip_address`, `user_agent`

### 5.2 Revogação
- Paciente pode revogar consentimento a qualquer momento pelo app
- Notificação automática ao DPO (Data Protection Officer) da clínica
- Prazo de atendimento: 15 dias corridos (Art. 18, LGPD)
- Fluxo de trabalho de revogação rastreado em `ConsentRevocationWorkItem`

### 5.3 Direitos do Titular (DSAR — Data Subject Access Request)
| Direito | Implementação |
|---------|---------------|
| Acesso | Exportação de dados pelo app em até 15 dias |
| Correção | Via atendimento pela clínica com registro de auditoria |
| Exclusão | Anonimização após período de retenção legal |
| Portabilidade | Exportação em JSON estruturado |
| Informação | Política de privacidade acessível no app |

---

## 6. Segurança da Aplicação

### 6.1 Autenticação
- **Sessão web:** Django Session + CSRF (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
- **API mobile:** JWT Bearer com refresh rotativo (expiração: 24h access / 30d refresh)
- **MFA:** suporte a TOTP (RFC 6238)

### 6.2 Autorização
- RBAC baseado em grupos Django + políticas por recurso
- Middleware de tenant evita vazamento de dados entre clínicas
- API mobile: `PatientBearerAuth` — tokens de paciente **nunca** autenticam rotas clínicas

### 6.3 Headers de Segurança (produção)
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Content-Security-Policy: default-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
```

### 6.4 Proteção contra Ataques Comuns
| Ameaça | Mitigação |
|--------|-----------|
| SQL Injection | ORM Django (queries parametrizadas) |
| XSS | Auto-escaping Django templates |
| CSRF | Token obrigatório em todos os formulários POST |
| Clickjacking | `X-Frame-Options: SAMEORIGIN` |
| Brute Force | Rate limiting via Nginx + Cloudflare |
| Secrets em código | Scanner de segredos no CI + `.env` para produção |

---

## 7. Internacionalização e Acessibilidade

### 7.1 Idiomas Suportados
- **pt-BR** (padrão) — catálogo completo compilado
- **en** — catálogo completo compilado  
- **es** — catálogo completo compilado

Implementação: `django.middleware.locale.LocaleMiddleware` + `gettext` com arquivos `.po`/`.mo`.

### 7.2 Acessibilidade (WCAG 2.1 AA)
- Elemento `<a class="skip-link">` para navegação por teclado em todas as páginas
- Atributos `aria-label`, `aria-describedby` e `role` em componentes interativos
- Contraste mínimo 4.5:1 em texto normal e 3:1 em texto grande (design system Aurora)
- Fontes auto-hospedadas (sem dependência de CDN externo no CSP)

---

## 8. Disponibilidade e Backup

### 8.1 SLA
- **Meta de disponibilidade:** 99,5% mensal (excluindo manutenções programadas)
- **Health checks:** `/health/live/` (liveness) e `/health/ready/` (readiness)
- **Monitoramento:** métricas de latência em `/health/metrics/` (Prometheus-compatible)

### 8.2 Backup e Recuperação
| Item | Valor |
|------|-------|
| Frequência | Diária (00:00 UTC) |
| Retenção | 30 dias |
| Destino | Google Drive (criptografado AES-256) |
| RTO estimado | < 4 horas |
| RPO | < 24 horas |

---

## 9. Controle de Versão e Deploy

- **Repositório:** GitHub (`RuiGN/auroraelo`, branch `gemini`)
- **CI/CD:** deploy manual autorizado com `git pull --ff-only` + `docker build`
- **Verificações pré-deploy:**
  - `pytest` (260 testes)
  - `ruff check` + `ruff format --check`
  - `mypy` (zero erros reais)
  - `python manage.py check`
  - `python manage.py makemigrations --check`
  - E2E Playwright (37 testes)

---

*Documento gerado automaticamente a partir do estado da branch `gemini` (Sprint 9).*  
*Para atualizar: `python manage.py generate_spec_docs` (planejado para Sprint 10).*
