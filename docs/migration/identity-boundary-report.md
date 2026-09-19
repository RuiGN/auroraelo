# Relatório de fronteiras de identidade — Sprint 03

Data da verificação: 2026-09-08.

## Escopo

Este relatório fecha as lacunas de evidência S03.02 e S03.03 descritas em
`docs/migration/evidence/sprint-03.md`. A cobertura foi adicionada em
`tests/test_identity_migration_boundaries.py`, sem alteração da política ou dos
serviços de produção.

## S03.02 — expiração temporal do TOTP

`test_expired_totp_challenge_does_not_grant_mfa_session` fixa o relógio já usado
por `accounts.services`, matricula e confirma o fator no instante inicial e
gera, sem consumir, o TOTP do passo seguinte. O endpoint recebe esse código 90
segundos depois do instante em que ele seria válido. Esse avanço o coloca fora
da tolerância implementada de um passo anterior ou posterior.

O teste comprova que o endpoint mantém HTTP 200 com erro de código inválido ou
já utilizado, não grava `mfa_verified` na sessão e não avança
`UserMFA.last_used_step`. Assim, o material expirado não concede confiança MFA
nem altera o estado de consumo. Uma segunda submissão, agora com o TOTP do
relógio corrente, é aceita e grava `mfa_verified`; isso separa a expiração de
uma eventual negativa por replay ou por erro no arranjo do relógio.

## S03.03 — superusuário técnico sem vínculo clínico

`test_technical_superuser_without_membership_has_no_clinical_scope` cria uma
clínica ativa e um superusuário Django ativo, sem `ClinicMembership`. Mesmo com
o identificador válido da clínica no cabeçalho, o acesso HTTP ao workspace é
negado com 403 e a mensagem tenant-safe existente.

O mesmo teste afirma que `ClinicAuthorizationPolicy` retorna `False` para
`clinic.read`. Isso comprova nas duas fronteiras relevantes que privilégios de
framework não substituem vínculo clínico ativo.

## Verificação focada

Banco isolado: origem `mindcare_identity`, banco de teste Django
`test_mindcare_identity`, PostgreSQL em `127.0.0.1:55439`. Nenhuma fonte de
ambiente do projeto ou dado real foi carregado.

Comando executado:

```text
env -i PATH="$PATH" DJANGO_SETTINGS_MODULE=config.settings.test TEST_DATABASE=postgresql DB_NAME=mindcare_identity DB_HOST=127.0.0.1 DB_PORT=55439 DB_USER=mindcare DB_PASSWORD=mindcare-test-only .venv/bin/pytest tests/test_identity_migration_boundaries.py --reuse-db --no-cov -q
```

Resultado final: `2 passed in 1.47s`.

Comando executado:

```text
.venv/bin/ruff check tests/test_identity_migration_boundaries.py && .venv/bin/ruff format --check tests/test_identity_migration_boundaries.py
```

Resultado: `All checks passed!` e `1 file already formatted`.

Comando executado após a integração com o gate tipado:

```text
env -i PATH="$PATH" DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/mypy tests/test_identity_migration_boundaries.py
```

Resultado: `Success: no issues found in 1 source file`.

O primeiro ciclo de pytest foi interrompido após revelar uma falha exclusiva do
arranjo inicial: a fonte global de aleatoriedade havia sido fixada e produziu
códigos de recuperação duplicados. A interferência foi removida; ela não indicou
defeito no backend. O ciclo final acima passou integralmente.
