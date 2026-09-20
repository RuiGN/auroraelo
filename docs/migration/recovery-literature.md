# Literatura pública para apoio à recuperação — Aurora Elo

**Estado:** corpus curado para revisão clínica; não é protocolo de tratamento nem liberação da IA.
**Acesso às fontes:** 2026-09-20. **Idioma canônico:** pt-BR; en/es planejados, não produzidos nesta tarefa.
**Artefato:** `ai_assistant/knowledge/recovery_sources.json`, `schema_version=1`, 10 fontes únicas.

## Escopo e método

Curadoria focal de páginas institucionais originais da OMS, NICE, NIAAA e NCCIH e de uma revisão Cochrane, sem blogs ou agregadores como base de afirmações.
“Fonte primária” significa aqui publicação no órgão/editor original: fichas, diretrizes e revisões são **sínteses**, não estudos clínicos primários individuais.
Houve busca atual, recuperação real das páginas e leitura dos trechos pertinentes; não se trata de revisão sistemática ou varredura exaustiva da literatura.
A pesquisa abrangeu álcool, outras substâncias, apostas/jogos de azar, retorno ao uso/jogo, TCC, entrevista motivacional, exercício, yoga e atividades artísticas.

A extração web configurada falhou por backend de busca sem capacidade de extração. A alternativa utilizada foi download HTTPS público, extração textual com `html.parser` e, no relatório de artes, `pypdf` em ambiente descartável fora do projeto.
A página NCBI do relatório de artes devolveu uma verificação de navegador: foi rejeitada como evidência, mesmo com resposta HTTP bem-sucedida. O PDF original da OMS foi obtido pelo link da página institucional, com leitura focal das páginas impressas 16–17, 30–32 e 51 (páginas 28–29, 42–44 e 63 do PDF).[22]
Os resumos abaixo distinguem resultados clínicos, benefícios gerais de bem-estar e regras editoriais do produto. Os trechos em inglês ao final são cópias curtas verificadas, não traduções inventadas.

## Síntese e limites de aplicação

### Álcool e outras substâncias

- O NIAAA descreve o transtorno por uso de álcool como condição médica tratável, com possibilidade de recuperação e de retornos ao uso durante o cuidado; isso não justifica linguagem de fracasso moral.[9]
- **Interrupção do álcool não deve virar desafio autoguiado:** quadros graves podem precisar de assistência médica e a síndrome de abstinência após consumo intenso prolongado pode ameaçar a vida; orientar avaliação médica e, diante de quadro agudo grave, ajuda humana urgente, não um plano automático de desintoxicação.[9]
- A TCC descrita pelo NIAAA trabalha situações desencadeantes e habilidades de enfrentamento; a terapia de reforço motivacional explora razões e planos de mudança; desintoxicação isolada não equivale a tratamento continuado.[16]
- A revisão Cochrane permite dizer que entrevista motivacional **pode** reduzir uso no curto prazo diante de nenhuma intervenção, mas pode fazer pouca ou nenhuma diferença diante de tratamento habitual ou outra intervenção ativa; a confiança nos resultados é limitada e as buscas chegam a novembro de 2022.[13]
- A OMS diferencia o conceito de substância psicoativa de potencial de dependência e inclui prevenção, tratamento e redução de danos na resposta de saúde pública; a página não é um instrumento para diagnosticar quem relata uso.[8]

**Limite editorial:** acolhimento, registro voluntário de situações difíceis e preparação de perguntas para profissionais são usos propostos de psicoeducação, não intervenções digitais cuja eficácia tenha sido demonstrada por essas fontes. Não se atribui ao Aurora Elo o desempenho de outro programa digital.

### Jogo de azar, prevenção de recaída e cuidado continuado

- A NICE NG248 recomenda TCC para reduzir gravidade e frequência do jogo prejudicial e inclui prevenção de recaída; a entrevista motivacional é considerada para fortalecer confiança e compromisso com a mudança, com atendimento por profissionais habilitados e capacitados.[17]
- A diretriz orienta não tratar recaída como fracasso individual e manter apoio, seguimento e possibilidade de retorno rápido à terapia conforme necessidades; essas recomendações não representam garantia de ausência de recaída.[17]
- Risco considerável ou imediato demanda encaminhamento urgente a serviço especializado ou equipe de crise, inclusive via emergência quando necessário.[17]

**Limite de população:** o tema `gambling` identifica apostas/jogos de azar; não valida intervenções para videogames ou para toda faixa etária por analogia. O corpus exclui medicamentos, doses e esquemas de tratamento.

### Exercício, yoga e artes: complementos, não substitutos

- **Atividade física:** a página da OMS sustenta benefícios gerais de saúde mental, qualidade de vida e bem-estar; não fornece, nessa página, demonstração de prevenção de recaída em álcool, drogas ou jogo.[18]
- **Yoga:** o NCCIH descreve pequena base de pesquisa em programas de tratamento de uso de substâncias e desfechos que misturam consumo, dor, estresse e ansiedade; redução de ansiedade não pode ser convertida em prova de abstinência ou prevenção de recaída duradoura.[5]
- **Segurança da yoga:** o NCCIH recomenda instrutor qualificado e alerta para riscos da prática sem supervisão; o produto não deve impor rotinas universais nem substituir avaliação individual.[5]
- **Artes/arteterapia:** a revisão de escopo da OMS relata achados de musicoterapia sobre controle percebido e fissura em dependências, com incerteza sobre motivação e enfrentamento; esses resultados não comprovam eficácia da arteterapia visual nem de uma atividade criativa autoguiada contra recaída.[22]
- A revisão de artes combina métodos e populações e declara não ter realizado busca sistemática; musicoterapia, arteterapia profissional e lazer artístico não devem ser tratados como a mesma intervenção.[22]

**Decisão editorial:** exercício e artes podem aparecer como opções de bem-estar; yoga e arteterapia devem estar explicitamente rotuladas como complementares, com evidência específica limitada. Não oferecer promessas de cura, “detox”, substituição de cuidado ou eficácia preventiva de recaída. Não interpretar desenhos como diagnóstico nem chamar uma atividade do aplicativo de arteterapia profissional.

### Crise suicida e identidade do avatar

- A OMS orienta procurar pessoas de confiança e profissionais diante de pensamentos suicidas; perigo imediato requer contato com emergência ou linha de crise, e quem acompanha a pessoa não deve deixá-la sozinha enquanto busca ajuda.[20]
- A OMS alerta que modelos de linguagem imitam a comunicação humana e podem produzir respostas plausíveis, porém inteiramente incorretas em saúde; transparência, supervisão especializada e avaliação rigorosa são necessárias.[19]

**Requisitos do produto, não resultados de ensaio:**

- Identificação visível: **“Sou uma IA de apoio digital, não uma pessoa, psicólogo ou serviço de emergência.”** Avatar, imagem, voz e linguagem não devem simular identidade de profissional humano.
- Manter a IA **desativada até API própria e revisão clínica independente**. Esta entrega é conteúdo estático e não verifica nem modifica flags, integração, Redis, provedor ou estado operacional.
- Não prometer atendimento de crise, vigilância contínua, socorro já acionado, resposta em tempo real ou relacionamento terapêutico humano.
- Ajuda humana de emergência tem prioridade sobre continuar a conversa; números e serviços locais precisam de validação própria antes de publicação.
- Não gerar diagnóstico, prescrição, doses, retirada de medicamentos ou protocolos individuais de abstinência.

## Inventário canônico e rastreabilidade

As datas nulas significam ausência de data original de publicação identificada, não ausência de leitura. NIAAA informa atualização em janeiro de 2025 e NCCIH em agosto de 2023; atualização não foi convertida silenciosamente em publicação.[9][5]

| ID do corpus | Editor | Escopo da leitura / natureza | Ledger |
|---|---|---|---|
| `niaaa-understanding-alcohol-use-disorder` | NIAAA | Ficha educativa; quadro, cuidado, recuperação e abstinência | [9] |
| `niaaa-alcohol-treatment-faq` | NIAAA | FAQ; terapias comportamentais, desintoxicação e cuidado continuado | [16] |
| `nice-gambling-harms-ng248` | NICE | Recomendações clínicas; seções 1.1, 1.5 e 1.6 | [17] |
| `cochrane-motivational-interviewing-substance-use` | Cochrane | Resumo público e abstract completo da revisão sistemática | [13] |
| `who-psychoactive-drugs` | WHO | Página temática; Overview, Impact e WHO response | [8] |
| `nccih-yoga-effectiveness-safety` | NCCIH | Seções sobre substâncias, ansiedade, segurança e atualização | [5] |
| `who-arts-health-scoping-review` | WHO Regional Office for Europe | PDF completo preservado; leitura focal de resultados e limitações | [22] |
| `who-physical-activity` | WHO | Página temática; visão geral e benefícios, não eficácia em dependências | [18] |
| `who-suicide-human-help` | WHO | Perguntas e respostas; orientações para pessoa e rede de apoio | [20] |
| `who-safe-ethical-ai-health` | WHO | Comunicado completo de riscos e governança, não estudo de eficácia | [19] |

## Auditoria e reprodução local

- Ledger separado: `/Users/rgnsystems/.hermes/cache/scratch/aurora-literature-ledger.json`.
- Extrações, HTML original, PDF e resultados: `/Users/rgnsystems/.hermes/cache/scratch/aurora-literature-evidence/`.
- `audit-manifest.json`: mapeamento de cada ID do corpus ao ID do ledger, URL, arquivo de evidência e SHA-256.
- `quote-verification.json`: resultado de cada `sources.py quote ID --text TRECHO --from EXTRAÇÃO`.
- `validate_corpus.py` e `validation.json`: contrato JSON, tipos, IDs ASCII, temas autorizados, datas, duplicação e correspondência entre citações, ledger e extrações.
- `citation-verification.txt`: saída real de `sources.py verify --evidence` para este relatório.
- `clinical-claims.md` e `clinical-citation-verification.txt`: recorte das 15 afirmações externas da síntese, verificado com `--evidence --min-coverage 1.0` (100% com citações).

A tentativa inicial de exigir 50% de cobertura no relatório inteiro falhou porque o denominador também inclui método, auditoria e requisitos próprios do produto; a saída foi preservada em `citation-verification-initial.txt`. O relatório completo passa pelo gate de identidade/evidência, enquanto o recorte científico passa adicionalmente pelo gate de cobertura de 100%. Não foram adicionadas citações artificiais para atribuir decisões do produto às fontes.

Os IDs históricos do ledger foram preservados; registros antigos ou descartados não são automaticamente fontes aprovadas. Apenas os registros do JSON canônico integram o corpus. O mirror NCBI bloqueado, a metanálise de exercício em outro editor e os demais candidatos não selecionados não sustentam as conclusões desta entrega.
O bloco `Sources` abaixo é gerado pelo script a partir do ledger; cada fonte citada tem evidência literal anexada. O verificador valida identidade e presença de trechos, não substitui avaliação crítica ou revisão clínica.
Os arquivos em scratch são temporários e sujeitos à limpeza do ambiente: antes de aprovação/publicação, o responsável deve transferir as evidências para armazenamento de auditoria com retenção definida.

```sh
python3 /Users/rgnsystems/.hermes/cache/scratch/aurora-literature-evidence/validate_corpus.py
python3 /Users/rgnsystems/.hermes/skills/research/grounded-citations/scripts/sources.py \
  --ledger /Users/rgnsystems/.hermes/cache/scratch/aurora-literature-ledger.json \
  verify docs/migration/recovery-literature.md --evidence
```

## Lacunas e gate de publicação

- Não foram realizados busca sistemática, GRADE próprio, validação linguística en/es, avaliação da rede brasileira ou ensaio clínico do aplicativo.
- Não há, neste conjunto, prova de que exercício, yoga, arteterapia visual ou avatar de IA previnam recaída no público do Aurora Elo.
- Diretrizes estrangeiras e conteúdo público exigem adaptação clínica/local; disponibilidade pública não implica licença irrestrita para reprodução integral. O corpus mantém paráfrases e trechos curtos; as extrações integrais ficam fora do repositório.
- Exigir revisão clínica independente, validação dos encaminhamentos de crise, avaliação de direitos/licenças e atualização das fontes antes de liberar conteúdo ou IA ao público.
- Evidência desta entrega: pesquisa e validação documental local; nenhuma alegação de funcionamento em produção.

## Sources

[5] https://www.nccih.nih.gov/health/yoga-what-you-need-to-know — NCCIH: Yoga what you need to know
    > "A small amount of research has looked at the possible benefits of incorporating yoga into treatment programs for various types of substance use disorders (opioid, alcohol, or tobacco use disorders or others)."
    > "In a 2021 review of 8 studies (1,889 participants), 7 studies showed evidence of beneficial effects in terms of reduced use of the substance or reduction in symptoms such as pain, stress, or anxiety."
    > "Practice yoga under the guidance of a qualified instructor. Learning yoga on your own without supervision has been associated with increased risks."
[8] https://www.who.int/health-topics/drugs-psychoactive — WHO health topic: Drugs (psychoactive)
    > "“Psychoactive” does not necessarily imply dependence-producing,"
    > "The use of psychoactive drugs without medical supervision is associated with significant health risks and can lead to the development of drug use disorders."
[9] https://www.niaaa.nih.gov/publications/brochures-and-fact-sheets/understanding-alcohol-use-disorder — NIAAA: Understanding Alcohol Use Disorder
    > "People with severe AUD may need medical help to avoid alcohol withdrawal if they decide to stop drinking."
    > "Alcohol withdrawal is a potentially life-threatening process that can occur when someone who has been drinking heavily for a prolonged period of time suddenly stops drinking."
    > "Many people with AUD do recover, but setbacks are common among people in treatment."
    > "Behavioral treatments—also known as alcohol counseling, or talk therapy, and provided by licensed therapists—are aimed at changing drinking behavior."
[13] https://www.cochrane.org/evidence/CD008063_does-motivational-interviewing-help-people-reduce-their-use-alcohol-drugs-or-both — Cochrane: Motivational interviewing for substance use reduction
    > "Motivational interviewing may reduce substance use compared with no intervention up to a short follow-up period."
    > "MI may make little to no difference to substance use compared to treatment as usual and another active intervention."
    > "Overall, we have moderate to no confidence in the evidence, which forces us to be careful about our conclusions."
[16] https://alcoholtreatment.niaaa.nih.gov/FAQs-searching-alcohol-treatment — FAQs: Searching for Alcohol Treatment | Navigator | NIAAA
    > "This form of therapy is focused on identifying the feelings and situations (called “cues”) that lead to heavy drinking, and managing stress that can lead to relapse."
    > "Detox alone is not the same as treatment."
    > "The therapy focuses on helping the patient identify the pros and cons of seeking treatment, form a plan for making changes in drinking behavior, build confidence, and develop the skills needed to stick to the plan."
[17] https://www.nice.org.uk/guidance/ng248/chapter/Recommendations — Recommendations | Gambling-related harms: identification, assessment and management | Guidance | NICE
    > "Offer group CBT to reduce gambling severity and frequency."
    > "Consider motivational interviewing to strengthen people's confidence and commitment to change, or to encourage people who are unsure or have reservations about starting treatment."
    > "include a relapse prevention component (covering, for example, how to deal with triggers and how to respond to a relapse)."
    > "relapse does not indicate individual failure, and having a plan in place to recover quickly increases confidence and reduces shame"
    > "If a person experiencing gambling-related harms presents considerable or immediate risk to themselves or others, refer them urgently to specialist mental health services or a crisis team, via the emergency services if necessary."
[18] https://www.who.int/health-topics/physical-activity — Physical activity
    > "It also helps to maintain a healthy body weight and can improve mental health, quality of life and well-being."
    > "Popular ways to be active include walking, cycling, wheeling, sports, active recreation and play, and can be done at any level of skill and for enjoyment by everybody."
[19] https://www.who.int/news/item/16-05-2023-who-calls-for-safe-and-ethical-ai-for-health — WHO calls for safe and ethical AI for health
    > "LLMs generate responses that can appear authoritative and plausible to an end user; however, these responses may be completely incorrect or contain serious errors, especially for health-related responses;"
    > "This includes widespread adherence to key values of transparency, inclusion, public engagement, expert supervision, and rigorous evaluation."
    > "LLMs include some of the most rapidly expanding platforms such as ChatGPT, Bard, Bert and many others that imitate understanding, processing, and producing human communication."
[20] https://www.who.int/news-room/questions-and-answers/item/suicide — Suicide
    > "If you think someone is in immediate danger, don't leave them alone. Contact the emergency services, a crisis line, a health worker or a family member."
    > "Talk to a health worker, such as a doctor or mental health professional, or a counsellor or social worker."
[22] https://iris.who.int/server/api/core/bitstreams/e1cc8536-773d-446f-9822-8ae376f41415/content — WHO Europe — Arts and health, HEN 67 (full report)
    > "Studies on addiction have reported benefits of music therapy for improving perceived control (572) and reducing cravings (573), although whether there are other benefits such as for motivation or coping skills remains unclear (572,574)."
    > "First, this report did not involve a systematic literature search, as this would have produced too many results for an effective synthesis."
