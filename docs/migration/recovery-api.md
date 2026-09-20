# Biblioteca pública e API de apoio à recuperação

## Estado e bloqueios deliberados

Implementação isolada em `ai_assistant/recovery_*.py`; conector comercial **desativado
por padrão**. Não usa assinatura, login, provider ou configuração do Hermes.
Nenhum teste chama LLM real. Não há embeddings, treinamento, vector DB, sessões de
chat, armazenamento de relatos, diagnóstico, terapia ou acionamento de emergência.

**Integração B2C ainda depende do principal:** o catálogo fechado de
`consents.policies.ConsentPurpose` não contém `recovery_library`/`recovery_ai`; os
serviços/documentos/manifestações existentes exigem `clinic_id`. Reutilizar
`clinical_follow_up`, `communication`, consentimento antigo presumido ou selecionar
uma clínica artificial não autoriza IA B2C. Esta entrega NÃO cria consentimento
persistido B2C nem altera o catálogo, modelos ou migrations existentes.

A API é executável com um adaptador explícito de consentimento; sem ele, nega acesso
com 403. O teste usa um adaptador **sintético em memória** para exercitar manifestação,
revogação e troca de ator. Isso prova a fronteira de autorização, **não persistência
B2C real**. Ativação depende de implementação/revisão dessa fronteira pelo principal,
credenciais próprias de produção e aprovação clínica independente.

## URLs e integração exata proposta

O URLconf novo contém paths completos, sem prefixo adicional:

- `POST /api/v1/recovery/library/` — nome `recovery-library`.
- `POST /api/v1/recovery/assistant/` — nome `recovery-assistant`.

O principal deve incluir `path("", include("ai_assistant.urls"))` no URLconf raiz.
Não foi alterado `config/urls.py` nesta entrega.

O middleware atual tenta resolver uma clínica para qualquer autenticado fora de
`/accounts/`, `/admin/`, `/health/`. **Proposta de exceção exata**, a revisar no
contrato público de políticas adotado pelo principal:

```python
RECOVERY_B2C_PATHS = frozenset({
    "/api/v1/recovery/library/",
    "/api/v1/recovery/assistant/",
})
# No ponto anterior a resolve_request_clinic():
# request.path in RECOVERY_B2C_PATHS → não resolver clínica;
# a view continua exigindo sessão, ator ativo, CSRF e consentimento B2C.
```

Não usar `startswith('/api/')`, `startswith('/api/v1/recovery/')`, `csrf_exempt`,
query de membership sem escopo ou bypass geral de autenticação. As views rejeitam
**toda querystring**, `X-Clinic-ID` e campos não previstos no JSON, incluindo
`actor_id`, `user_id`, `patient_id`, `clinic_id`, `provider`, `endpoint`, `mode`.
Não há queryset de tenant nesta vertical. O ator vem exclusivamente de `request.user`.

Manter SessionMiddleware, AuthenticationMiddleware, controles de sessão existentes
e CsrfViewMiddleware. O principal pode configurar:

```python
CSRF_FAILURE_VIEW = "ai_assistant.recovery_views.recovery_csrf_failure"
```

Esse hook responde JSON 403 **somente nos dois paths exatos**, delegando os demais
à falha CSRF padrão do Django. Se o projeto possuir outro handler customizado,
compor essa delegação no handler existente em vez de substituí-lo globalmente.
Sem o hook, a proteção continua válida, porém o erro CSRF é HTML Django.
Não há endpoint novo para obter token: usar o cookie/token atualizado do fluxo
existente de autenticação. POST requer cookie de sessão e `X-CSRFToken` correspondente;
origem/referer continuam validados pelo Django. Anônimo sem token pode receber 403
CSRF antes do 401 de autenticação. Não há JWT nem autenticação B2B implícita.

## Contrato de consentimento servidor

`RECOVERY_CONSENT_RESOLVER` deve ser `None` (padrão) ou callable servidor, não caminho
fornecido pelo cliente. Assinatura:

```python
resolver(*, actor: AbstractBaseUser, purpose: str) -> RecoveryConsent | None
```

`RecoveryConsent` está em `ai_assistant.recovery_access`:

| Campo | Tipo/semântica |
|---|---|
| `subject_id` | UUID exatamente igual ao usuário autenticado |
| `purpose` | `recovery_library` ou `recovery_ai`, exatamente a finalidade pedida |
| `document_version` | string não vazia, até 100 caracteres |
| `explicit` | booleano `True`, não valor truthy |
| `accepted_at` | datetime consciente de fuso, não futuro |
| `expires_at` | datetime consciente de fuso, posterior ao instante atual |
| `revoked_at` | deve ser `None` |

**Obrigações do adaptador:** consultar a última manifestação persistida do próprio
ator a cada invocação; conferir documento vigente, integridade, finalidade e versão;
revogação/recusa/supersessão devem invalidar a decisão imediatamente, sem cache de
aceitação. `recovery_ai` precisa cobrir envio de mensagem e histórico ao processador
explicitamente contratado e aprovado; aceite de biblioteca não cobre esse envio.
O adaptador não pode consultar tenant por payload, inferir consentimento de um papel,
aceitar um booleano HTTP ou produzir grant por existência de qualquer consentimento.

`authorize()` confirma também a existência/atividade atual no banco de identidades
via `core.policies.current_actor_is_active`. Falha do adaptador/banco nega acesso.
A autorização é repetida antes do envio e antes da entrega; revogação durante o
transporte descarta a resposta. Dados que já saíram antes da revogação não podem ser
retirados por essa checagem: retenção/eliminação do processador é obrigação contratual.
Nenhuma transação de banco é mantida aberta durante chamada HTTP.

## Payloads e respostas

Biblioteca:

```json
{"query":"atividade física", "topics":["exercise"], "language":"pt-br"}
```

Somente `query` é obrigatório. `topics` default `[]`, `language` default `pt-br`.
Resposta 200: `identity`, `mode="library"`, `retrieval="lexical"`, `sources`,
`corpus_version`, `content_language="pt-br"`, `quote_language="original"`,
`supported_content_languages=["pt-br"]`, `notice`.
Cada source preserva os campos canônicos descritos abaixo, inclusive URL,
`evidence_quote`, `evidence_limitations`, `safety_notes` e datas. São trechos
educativos correspondentes às palavras, não uma resposta clínica à pergunta.

Assistente (apenas depois de todas as aprovações):

```json
{
  "message":"Quero aprender sobre atividade física.",
  "history":[{"role":"user","content":"Exemplo de histórico sintético."}],
  "topics":["exercise"],
  "language":"pt-br"
}
```

Somente `message` é obrigatório; `history` default `[]`. Não há IDs de conversa.
Resposta 200: `identity`, `mode="assistant"`, `answer`, `citations`, `sources`,
`content_language="pt-br"`, `corpus_version`, `notice`.
Citação: `source_id`, `quote`, `url`, `title`, `evidence_limitations`, `safety_notes`.
URL/título/limitações vêm do corpus servidor, não do texto retornado pelo provider.
O frontend deve renderizar tudo como **texto**, nunca HTML confiável/`innerHTML`.

Identidade fixa: **Aurora Elo — apoio digital de IA**, não psicólogo humano.
Respostas das views usam `Cache-Control: no-store`, `Content-Language: pt-br` e
`X-Content-Type-Options: nosniff`.

| Status | `code` e significado |
|---|---|
| 200 | biblioteca, assistente validado ou orientação determinística `mode="safety"` |
| 400 | `invalid_input`: tipo, chave desconhecida, limites ou seleção de tenant |
| 401 | `authentication_required` |
| 403 | `consent_required`: inativo, consentimento ausente/revogado/errado, backend falho |
| 403 | `csrf_failed` com hook exato configurado; sem ele, HTML padrão Django |
| 405 | `method_not_allowed`: somente POST |
| 413 | `payload_too_large`: corpo excede 16.384 bytes |
| 415 | `unsupported_media_type`: somente `application/json` |
| 422 | `no_evidence`: zero correspondências; sem resposta inventada/LLM |
| 422 | `unsupported_content_language`: en/es solicitados, ainda não entregues |
| 429 | `usage_limit`, `Retry-After: 60`; quota diária pode exigir espera maior |
| 503 | `assistant_unavailable`: flag/aprovação/chave/config/transporte/resposta inválidos |
| 503 | `knowledge_unavailable`: Redis/config/versão/integridade/contador indisponíveis |

Erros usam `identity`, `code`, `detail`. Sem evidência inclui `mode="library"` e
`sources=[]`, inclusive quando a consulta originou no endpoint de assistente; não
há fallback fingindo inferência. Flag desativada retorna 503 antes do Redis para
consulta comum. Não transforma biblioteca em simulação de LLM.

### Limites e idiomas

- JSON estrito, sem chaves repetidas, NaN/Infinity, chaves extras ou conteúdo não JSON.
- Query/mensagem: 1–2.000 caracteres não vazios; corpo: máximo 16.384 bytes.
- Histórico: até seis itens; apenas `user`/`assistant`, exatamente role/content;
  cada content até 1.000 caracteres; total mensagem+histórico até 8.000.
- Tópicos: até oito, sem duplicatas, catálogo fechado abaixo.
- Recuperação: máximo três fontes, interseção lexical após normalização de acentos;
  filtros de tópicos reduzem o corpus **antes** da pontuação. Não há busca semântica.
- Resposta LLM: até 32.768 bytes; answer até 4.000 caracteres; 1–3 citações únicas,
  quote até 1.000 caracteres e substring literal de `evidence_quote` recuperado.
- Mensagens HTTP são extraíveis por gettext. A superfície está deliberadamente
  fixada em pt-br; **não há entrega/tradução completa en/es**, nem tradução de relatos.
  O plano trilingue depende de catálogos e revisão educativa/clínica em cada idioma.

### Salvaguardas

Padrões conservadores pt/en/es identificam menções a suicídio, overdose,
convulsões, abstinência grave, alucinações e dificuldade respiratória. Resposta fixa:
`mode="safety"`, `code="urgent_human_help"`, `notifies_emergency_services=false`,
encaminhamento humano (SAMU 192/emergência no Brasil; número local fora do Brasil;
CVV 188 como apoio emocional, não substituto de emergência médica).
Diagnóstico, prescrição/dose, promessa de abstinência, identidade humana e certos
jailbreaks são recusados com `code="clinical_boundary"`.

São regras limitadas, **não triagem clínica confiável nem detecção completa de
crise**. Falsos positivos/negativos exigem avaliação clínica independente. Mensagem
e histórico são examinados. Orientação fixa de segurança pode retornar mesmo com
conector desligado ou Redis indisponível, após autenticação/consentimento/limites de
entrada; não aciona equipe e não consome quota Redis. Rate limit de borda ainda é
necessário contra abuso desse caminho barato. Pedido explícito en/es é recusado
antes da análise do conteúdo; oferecer acesso público à emergência fora desta API.

## Corpus versionado e Redis HASH

Entrada exclusivamente pública e previamente revisada:

```json
{"schema_version":1,"sources":[{
  "id":"identificador-ascii-minusculo",
  "title":"Título", "publisher":"Publicador",
  "url":"https://example.org/fonte", "published_date":null,
  "accessed_on":"2026-09-20", "topics":["exercise"],
  "summary_pt_br":"Resumo educativo em português.",
  "evidence_quote":"Trecho literal no idioma original.",
  "evidence_limitations":"Limitações da evidência.",
  "safety_notes":["Não substitui avaliação profissional."]
}]}
```

Schema exato sem campos adicionais. `schema_version` inteiro 1, não booleano.
Até 2.000.000 bytes e 1–200 fontes. IDs únicos, até 80 caracteres,
`[a-z0-9]+(?:-[a-z0-9]+)*`; rejeita normalização silenciosa. Limites de caracteres:
title 500, publisher 300, URL 2.048, resumo/citação 6.000 cada, limitações 4.000.
Notas: 1–20 textos até 2.000 caracteres cada. Datas ISO `YYYY-MM-DD` válidas;
`published_date` pode ser null quando a data precisa não é conhecida.

Tópicos fechados: `alcohol`, `substances`, `gambling`, `relapse_prevention`,
`exercise`, `yoga`, `art_therapy`, `crisis`.
URLs exigem HTTPS, hostname DNS público sintaticamente válido, sem userinfo,
fragmento, espaço, barra invertida ou porta diferente de 443. IPs literais e nomes
locais são recusados. **Ingestão não acessa a URL**, portanto não verifica publicação,
fidelidade de citação, licença ou relevância clínica: tarefa do corpus/revisão humana.

Canonicalização: ordenar sources por ID e topics lexicalmente; preservar ordem das
notas e os textos; `json.dumps(sort_keys=True, ensure_ascii=False,
separators=(",", ":"))`, UTF-8. SHA-256 calculado desses bytes. Versão:
`v1-<sha256 de 64 hex minúsculos>`. HASH:

`auroraelo:knowledge:v1-<sha256>`

Cinco campos: `corpus` (JSON canônico), `sha256`, `schema_version`, `source_count`,
`language=pt-br`. São **apenas dados públicos**, não sessões, consentimentos ou chats.
Sem chave `latest`: API usa `RECOVERY_KNOWLEDGE_VERSION` fixada pelo deploy/revisão.
Atualizar fonte gera outra versão, não sobrescreve versões anteriores.

Uma operação Lua verifica inexistência ou igualdade exata dos cinco campos e aplica
um único HSET. Sync idêntico é no-op; conflito/corrupção falha sem reparar/sobrescrever
silenciosamente. Sempre há readback e comparação exata; `--verify` acrescenta outra
leitura de confirmação. Leitura Lua limita campos/tamanho, revalida schema, metadados,
SHA e versão solicitada; corpus incompleto/corrompido nunca serve conteúdo.

Uso compartilha apenas contadores expiráveis no Redis dedicado, em namespace
`auroraelo:recovery-usage:<HMAC-SHA256 do UUID>:minute|day` e `...:global:day`.
Não guarda UUID cru, IP, mensagem, histórico ou hashes de relatos. O HMAC exige chave
separada de pelo menos 32 caracteres. Quotas por ator/minuto, ator/dia e global/dia
são consumidas atomicamente por Lua; erro de Redis/contador/configuração nega uso.
Janelas começam na primeira requisição (60/86.400 segundos), não sliding window.

## Settings necessários (integração pelo principal)

| Setting | Default / restrição |
|---|---|
| `RECOVERY_KNOWLEDGE_REDIS_URL` | vazio; URL dedicada redis:// ou rediss://, sem query/fragmento; nunca fallback para cache/sessão |
| `RECOVERY_REDIS_TIMEOUT_SECONDS` | 2.0; 0.1–10, connect/read, sem retry |
| `RECOVERY_KNOWLEDGE_VERSION` | vazio; `v1-<sha256>` revisado |
| `RECOVERY_USAGE_HMAC_KEY` | vazio; segredo próprio >=32 caracteres |
| `RECOVERY_USAGE_PER_MINUTE` | 10; inteiro 1–60 |
| `RECOVERY_USAGE_PER_DAY` | 100; inteiro 1–1.000 |
| `RECOVERY_USAGE_GLOBAL_PER_DAY` | 10.000; inteiro 1–100.000 |
| `RECOVERY_CONSENT_RESOLVER` | None; callable servidor conforme contrato acima |
| `RECOVERY_AI_ENABLED` | False; somente booleano True habilita tentativa |
| `RECOVERY_AI_CLINICAL_APPROVED` | False; somente True após revisão clínica independente |
| `RECOVERY_AI_ENDPOINT` | vazio; URL HTTPS de API própria de produção |
| `RECOVERY_AI_ALLOWED_HOSTS` | (); tuple/list de hosts exatos, sem wildcard |
| `RECOVERY_AI_ALLOWED_PATHS` | (); tuple/list de paths exatos, ex. `/v1/chat/completions` |
| `RECOVERY_AI_API_KEY` | vazio; chave própria servidor, nunca Hermes/browser/mobile |
| `RECOVERY_AI_MODEL` | vazio; modelo explicitamente contratado |
| `RECOVERY_AI_TIMEOUT_SECONDS` | 5.0; 0.1–10 para sockets, leitura com deadline 3× |
| `CSRF_FAILURE_VIEW` | hook exato opcional explicado acima |

O principal deve mapear variáveis de ambiente para settings explicitamente e fazer
parse estrito de booleanos/números. Nenhum novo módulo lê `.env`, vault ou credenciais
do agente; passar `RECOVERY_*` apenas no shell **não configura Django sozinho**.
Produção requer Redis dedicado com TLS/ACL e proteção de rede. ACL do leitor não deve
poder alterar corpus; comando de publicação usa identidade autorizada distinta.
Os scripts precisam de EVAL/HGET/HGETALL/HLEN/HSTRLEN; sync exige EXISTS/HSET; quotas
exigem GET/TTL/INCR/EXPIRE no namespace próprio. Nada exige FLUSHALL.

## Transporte OpenAI-compatible

HTTPS ao host+path allowlisted; sem userinfo, query, fragmento, percent-encoding,
path traversal ou redirects. Resolve DNS, rejeita qualquer IP não global, conecta
a um dos IPs validados **sem resolver hostname novamente**, e valida certificado
TLS/SNI do hostname original (`ssl.create_default_context`). Não usa proxies,
`.netrc`, ferramentas do agente ou redirects automáticos. Não há retries.

Payload servidor: model explícito, temperature=0, max_tokens=800, stream=false,
store=false, n=1, response_format=json_object. Uma mensagem system fixa e um envelope
user JSON com mensagem/histórico/evidência marcados como não confiáveis. Não expõe
ferramentas. `store=false` é pedido ao processador, **não prova de retenção zero**.

Valida status 200, JSON MIME, corpo não comprimido e tamanho; rejeita finish_reason
incompleto, tool/function calls, refusal, esquema inesperado, links/HTML/dose ou
outros padrões proibidos, IDs externos e citações não literais. Isso verifica
**rastreabilidade mecânica**, não que todas as afirmações são cientificamente corretas
ou sustentadas pela citação. Avaliação clínica/semântica ainda obrigatória.

Limitação operacional: timeout de socket não limita a resolução DNS do sistema nem
constitui deadline absoluto para cada etapa de headers/TLS. O deadline de leitura
é verificado entre blocos. O principal deve exigir timeout duro do worker/proxy e
limites de egress/DNS antes de habilitar produção. Nenhuma garantia de SLA é feita.

## Verificação local e comandos

Sem migrations para ciclos TDD rápidos:

```bash
RECOVERY_TEST_REDIS_URL=redis://127.0.0.1:56389/13 \
  .venv/bin/python -m pytest tests/test_recovery_knowledge.py \
  tests/test_recovery_assistant.py --nomigrations --no-cov -q
```

O fixture só aceita **essa URL local DB13**, fornecida/reservada pelo principal.
Sem opt-in, testes que exigem Redis são skipped. Limpeza restrita aos namespaces
novos `auroraelo:knowledge:*` e `auroraelo:recovery-usage:*` nesse DB13; não usar DB13
simultaneamente para corpus que deva persistir. Sem FLUSHALL, Redis6379, VPS ou novos
containers. Indisponibilidade real é exercitada em porta local fechada com timeout
0.1s. LLM/HTTP/DNS externos são sempre mocks; nenhuma conversa real foi enviada.

Com migrations normais (settings SQLite de teste, sem banco real):

```bash
RECOVERY_TEST_REDIS_URL=redis://127.0.0.1:56389/13 \
  .venv/bin/python -m pytest tests/test_recovery_knowledge.py \
  tests/test_recovery_assistant.py tests/test_domain_architecture.py --no-cov -q
```

Execução final desta entrega: **143 testes passaram com migrations normais** em
587.08s, incluindo Redis8 real e os 42 testes de arquitetura. O ciclo rápido final
com `--nomigrations` também passou nos mesmos 143 casos (41.71s). Baseline de
arquitetura anterior: 42 passaram. Um ciclo inicial com migrations expirou no
limite 180s; as duas execuções completas posteriores passaram. A espera do job
final excedeu o timeout de uma chamada de ferramenta, mas o processo continuou
ativo e seu resultado final foi recuperado com exit code 0.

Publicação, após o principal fornecer os settings dedicados:

```bash
.venv/bin/python manage.py sync_recovery_knowledge \
  --settings=<settings_aprovados> \
  --corpus=ai_assistant/knowledge/recovery_sources.json --verify
```

Saída JSON contém `version`, `sha256`, `source_count`, `created` e `verified=true`.
Falha gera CommandError sem imprimir corpus/segredos. Comando executado via
`call_command` nos testes com JSON exclusivamente sintético e Redis8 real; corpus
real pertence ao agente de literatura e deve ser verificado pelo principal.

Gate local:

```bash
.venv/bin/python -m ruff check ai_assistant/recovery_*.py \
  ai_assistant/management/commands/*recovery*.py ai_assistant/urls.py \
  tests/test_recovery_knowledge.py tests/test_recovery_assistant.py
.venv/bin/python -m ruff format --check ai_assistant/recovery_*.py \
  ai_assistant/management/commands/*recovery*.py ai_assistant/urls.py \
  tests/test_recovery_knowledge.py tests/test_recovery_assistant.py
.venv/bin/python -m mypy ai_assistant/recovery_*.py \
  ai_assistant/management/commands/*recovery*.py ai_assistant/urls.py \
  tests/test_recovery_knowledge.py tests/test_recovery_assistant.py
```

A verificação mypy não acusa os arquivos novos após correções, mas alcança falhas
preexistentes em `config/celery.py` e `psychiatry/models.py`; não foram alterados nesta
vertical. Não declarar mypy global aprovado. Integração da rota/middleware real,
consentimento persistido B2C, corpus real, tradução trilingue, avaliação clínica e
operação/produção **não estão certificados por esses testes isolados**.

## Integração posterior do principal — bloqueada por padrão

Foram montados os dois paths em `config/urls.py`, com somente as duas exceções
exatas propostas em `core.policies.is_tenant_independent_path`. As exceções
dispensam resolução de clínica, não sessão, ator ativo, CSRF ou consentimento.
As nove exceções anteriores de psiquiatria permanecem separadas e inalteradas.

`RECOVERY_AI_ENABLED=False`, `RECOVERY_AI_CLINICAL_APPROVED=False` e
`RECOVERY_CONSENT_RESOLVER=None` agora são explícitos na base e importados por
development, production e test. Nesta versão não há mapeamento de ambiente para
ativar a IA nem adaptador B2C de produção. A tabela de settings acima descreve
o contrato para uma futura ativação revisada; não significa configuração entregue.
O handler global de CSRF não foi substituído: rejeições antecipadas podem usar
HTML, preservando a proteção original.

Evidência local do principal:

- TDD HTTP real: os dois paths retornavam 400 por falta de clínica; após a
  montagem restrita, retornam 403 `consent_required`, sem Redis ou provider.
- `tests/test_recovery_integration.py` verifica paths/sufixos, sessão revogada,
  usuário inativo, CSRF real, métodos, seleção antiga de clínica, identidade ou
  consentimento forjado no payload e ausência de chamadas externas. Um adaptador
  explicitamente sintético prova que consentimento de teste não liga a IA: 503.
- Execução conjunta com testes do domínio e arquitetura: **155 passed**, zero
  skips/failures/errors, Redis 8 real local DB13 e SQLite `--nomigrations`.
  É ciclo rápido; não substitui migrations normais nem aceite de produção.
  JUnit: `/Users/rgnsystems/.hermes/cache/scratch/recovery-parent-quick.xml`.
- O loader aceitou as dez fontes públicas reais de `recovery_sources.json`.
  Versão canônica: `v1-b4f37687c8f5fe5de4b4ac1fafcfcd551da4643fd61f7be0ef8d1b75acf35d35`.
- `sync_recovery_knowledge --verify` foi exercitado duas vezes somente no Redis
  descartável local: criação seguida de no-op, cinco campos e readback idêntico.
  Evidência: `/Users/rgnsystems/.hermes/cache/scratch/recovery-parent-corpus-sync.json`.
  Nenhum corpus foi publicado na VPS e nenhum dado de usuário foi ingerido.
- Ruff dos alvos de integração (exceto a base com baseline preexistente), Django
  check e `git diff --check` passaram. A base participa da comparação de gates
  global; não se declara Ruff/mypy global aprovado.

A nova fronteira de rotas está sob revisão independente. Permanecem bloqueios:
consentimento B2C persistido, revisão clínica, traduções educativas en/es,
configuração dedicada de produção e limites operacionais de transporte.
Não houve chamada LLM real, ativação, commit, push ou deploy desta integração.

## Correção do idioma HTTP após revisão independente

O parecer `recovery-integration-independent-review.json` reprovou a integração
por `RECOVERY-INTEGRATION-001`: `UserLanguageMiddleware` sobrescrevia o cabeçalho
pt-br das views por en/es, mesmo quando o corpo permanecia em português. O parecer
original é preservado. A revisão corretiva independente
(`recovery-language-corrective-review.json`, 2026-09-20) aprovou a correção
com `passed: true`: `setdefault` preserva o `Content-Language` explícito das
views recovery, respostas sem cabeçalho continuam recebendo a preferência
efetiva, e seleção de idioma, wrappers de stream, `Vary` e restauração não
foram alterados. Sem contradição identificada entre cabeçalho e corpo; os três
hashes dos arquivos revisados conferem com a árvore atual. Limitações
registradas: casos 403/503 revisados estaticamente, streams não consumidos nos
testes sem banco; aprovação limitada a RECOVERY-INTEGRATION-001, sem alcance
sobre psychiatry, produção ou ativação clínica.

O principal reproduziu quatro falhas HTTP nas duas rotas com perfis en/es, sessão
gerenciada, `ACCOUNT_SESSION_ALLOW_UNKNOWN=False`, CSRF válido e middlewares reais.
Sem resolver, o corpo 403 era português, mas `Content-Language` era en/es.

`accounts/middleware.py` agora usa `setdefault` para preservar o idioma declarado
pela view. Na ausência de cabeçalho explícito, continua aplicando a preferência
efetiva. Não altera idioma salvo, contexto de tradução, autenticação, tenant,
consentimento, CSRF, allowlist ou flags de IA. Os quatro casos RED passaram GREEN.

Cobertura complementar:

- Assistente desativado retorna 503 em pt-br para perfis pt-br/en/es, com CSRF real
  e sessão rastreada. O spy comprova `actor=request.user` e `purpose=recovery_ai`.
  O consentimento é exclusivamente um objeto sintético em memória; Redis e provider
  não são chamados nesses cenários.
- Seis casos de middleware sem banco verificam cabeçalho explícito/default para
  HTML, JSON e streaming, `Vary` do HTML e restauração do contexto. Os testes
  preexistentes de streams síncronos/assíncronos continuam exercitando o conteúdo.

Resultados relidos dos JUnit no scratch:

- Baseline fresco antes da mudança: **28 passed, 2 failed**, uma migration
  deselecionada no ciclo SQLite `--nomigrations`.
- Mesma regressão ampliada: **40 passed, 2 failed**, a mesma migration deselecionada.
  As duas falhas são as expectativas antigas de publicar somente pt-br; não foram
  removidas nem alteradas para aprovar esta correção.
- PostgreSQL descartável com migrations normais, Redis local reservado DB13 e
  nove módulos: **207 passed, 4 failed**, sem errors/skips. Inclui migration de
  preferência, autorização/sessões, integração, corpus, provider simulado, UI e
  arquitetura. Os dois erros adicionais são testes do shell que esperam 200 em `/`,
  mas recebem o redirecionamento 302 para login. Foram reproduzidos com o método
  real `UserLanguageMiddleware.__call__` de HEAD, carregado apenas no processo de
  teste, sem reverter o checkout. Não são introduzidos por `setdefault`.
- Ruff check/format dos três alvos passou. Mypy permanece reprovado com 35 erros
  em quatro arquivos de dependências, sem diagnóstico nos três alvos desta correção;
  isso não aprova o gate global. Há avisos de `staticfiles/` ausente.

Artefatos em `/Users/rgnsystems/.hermes/cache/scratch/`:
`recovery-language-{baseline,red,green,regression,postgresql}.xml`,
`recovery-language-shell-head-baseline.xml` e `recovery-language-mypy.log`.
O invólucro de baseline é `recovery_language_head_baseline.py` e não integra runtime.

Erros antecipados de CSRF e revogação de sessão continuam fora da resposta JSON da
view: podem ser HTML 403 ou redirecionamento 302. Esta correção não promete JSON,
identidade, idioma pt-br ou `no-store` nesses caminhos anteriores à view. A revisão
corretiva e os demais bloqueios de release permanecem pendentes; sem publicação.
