# Revisão independente de evidência

## Veredito

**Veredito final: especificação documental e qualidade dos testes focados
aprovadas após correção.**

A auditoria mantém S00.03, S00.04 e S00.06 abertas e separa inventário,
evidência funcional herdada e aceite ainda pendente. Foram reconciliados 54 nomes
de testes únicos citados em `contract-audit.md`; todos existem com grafia exata em
`evidence/destination-final-pytest.xml`. O mesmo JUnit registra 1.253 casos, zero
falhas e zero erros, incluindo 97 casos parametrizados de compilação de template.
A matriz de rotas contém 182 entradas. Essas evidências sustentam o caráter
parcial da auditoria, não a conclusão das três tarefas.

O gate global de 90% continua configurado e não foi reduzido. A evidência global
herdada permanece em 86%, registrada em `contract-audit.md:121-122`; o relatório
focado corrigido não faz nova alegação percentual e remete a decisão ao run de
integração em `coverage-report.md:55-64`.

## Achado inicial e resolução

### [Alta] Os testes do invariante SQL espelham as constantes da implementação

Na versão inicialmente revisada, em
`tests/test_migration_domain_invariants.py:28-59`, os valores esperados dos
quatro casos de instalação/remoção são as próprias constantes privadas
`_PG_STATEMENTS`, `_SQLITE_STATEMENTS`, `_PG_REVERSE` e `_SQLITE_REVERSE` do
módulo sob teste. O editor falso apenas acumula exatamente as strings recebidas.
Assim, uma alteração simultaneamente errada na constante e na função continua
verde; SQL inválido, trigger ausente, condição invertida e invariante inoperante
também passam. Os dois casos de vendor desconhecido em
`tests/test_migration_domain_invariants.py:62-77` só exercitam despacho.

Isso torna excessiva a apresentação de 100% em `coverage-report.md:36-55` como
evidência de cobertura útil das migrações de tenant. A afirmação mais estreita de
ordem de emissão em `coverage-report.md:11-14` é tecnicamente verdadeira, mas não
prova o comportamento descrito pelo nome do módulo nem pelo docstring do teste.
Seis dos dez casos focados pertencem a esse grupo estrutural; os quatro casos de
e-mail exercitam decisões observáveis de normalização, no-op, branco e duplicata.

A correção requerida foi retirar os testes autorreferenciais e sustentar qualquer
alegação sobre o invariante com efeitos no banco. A recomendação mais abrangente
foi testar instalação e reversão em cada backend suportado, com escrita same-tenant,
rejeição cross-tenant para versão e mídia e imutabilidade do tenant, sem importar
as constantes SQL privadas.

**Resolvido.** Os quatro casos que importavam as constantes privadas foram
removidos. Os seis casos restantes em
`tests/test_migration_domain_invariants.py:26-127` exercitam o fail-closed de
vendor desconhecido e os efeitos observáveis da canonicalização de e-mail. O
relatório registra explicitamente a remoção e sua razão em
`coverage-report.md:15-17`, distingue o indicador de progresso de cobertura em
`coverage-report.md:35-41` e elimina a antiga alegação de 100% de cobertura.

Os efeitos do invariante no banco permanecem cobertos pela suíte existente
`tests/test_content_tenant_invariant.py`: os quatro nomes constam no JUnit
herdado e verificam escrita same-tenant, rejeição de versão e mídia cross-tenant
e imutabilidade do tenant. Essa suíte não foi reexecutada nesta correção, limite
declarado em `coverage-report.md:62-64`. A reversão efetiva das triggers não tem
um teste comportamental identificado; o relatório corrigido também não a alega,
portanto isso fica como limitação residual, sem reabrir o achado.

## Auditoria de contratos

Não foi identificado defeito bloqueante nos dois documentos de auditoria. As
conclusões em `contract-audit.md:17-23` e as lacunas em
`contract-audit.md:106-125` são compatíveis com a evidência: não alegam mapeamento
1:1 de callback, renderização completa de contexto ou aceite visual. A proposta
em `contract-audit-report.md:48-67` preserva corretamente as três tarefas abertas.

## Escopo e protocolo

Os arquivos sob revisão foram `tests/test_migration_domain_invariants.py`,
`docs/migration/coverage-report.md`, `docs/migration/contract-audit.md` e
`docs/migration/contract-audit-report.md`. As matrizes, o código das duas
migrações, `tests/test_content_tenant_invariant.py` e o JUnit existente foram
consultados somente para conferir as alegações. Nenhum teste foi reexecutado.
Nenhum arquivo de backend, configuração ou gate foi alterado.
