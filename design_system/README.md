# 🌌 Aurora Elo Design System

> **Integração Django atual:** veja [INTEGRATION.md](INTEGRATION.md).
> O texto abaixo descreve o showcase histórico, não funcionalidades clínicas
> verificadas. O runtime integrado usa Tailwind 3.4.17 compilado localmente,
> gettext e fontes de sistema; não usa o CDN nem o tradutor JavaScript.
> **Sistema de Design Oficial para Clínica Psiquiátrica & Ecossistema de Aplicativos Mobile**  
> Desenvolvido em **Tailwind CSS (Última Versão)** com suporte completo a **Português (pt-BR)**, **Inglês (en)** e **Espanhol (es)**.

---

## 🧭 1. Conceito da Marca & Inspiração Visual

O design system foi construído a partir do logotipo oficial **Aurora Elo**:
- **Aurora (Azul Marinho Noturno `#0A2540` / `#051424`):** Simboliza o rigor clínico, a segurança psiquiátrica, o acolhimento protetor e a serenidade terapêutica.
- **Elo (Ciano & Cerúleo Vibrante `#0284C7` / `#06B6D4`):** Representa a aliança terapêutica, a conexão neural, a clareza mental e o renascimento de uma nova aurora.
- **Acelerações Cromáticas Clínicas:**
  - 🌿 **Estabilidade / Eutimia (`#10B981`):** Recuperação, adesão farmacológica bem-sucedida e alta médica.
  - ⚠️ **Atenção / Moderação (`#F59E0B`):** Efeitos adversos, sintomas residuais e monitoramento intensivo.
  - 🚨 **Crise Psiquiátrica / SOS (`#F43F5E`):** Alerta agudo, risco de autoextermínio, agitação psicomotora e linha de plantão 24h.
  - 🔮 **Mindfulness & TCC (`#8B5CF6`):** Exercícios cognitivos, neurofeedback e higiene do sono.

---

## 📱 2. Ecossistema Multiplataforma

O sistema foi arquitetado para unificar 3 produtos complementares:

```
                          ┌───────────────────────────┐
                          │   Aurora Elo Web Portal   │
                          │   (Clínica Psiquiátrica)  │
                          └─────────────┬─────────────┘
                                        │ Sincronização
                                        │ em Tempo Real
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
        ┌───────────────────────────────┐ ┌───────────────────────────────┐
        │   App 1: Aurora Elo Clínica   │ │    App 2: Aurora Mind (B2C)   │
        │   (Mobile Conectado ao EHR)   │ │    (Lojas de Apps / Retail)   │
        ├───────────────────────────────┤ ├───────────────────────────────┤
        │ • Prontuário na palma da mão  │ │ • Rastreamento diário de humor│
        │ • Teleconsulta criptografada  │ │ • Diário de Pensamentos (TCC) │
        │ • Checagem de remédios        │ │ • Respiração Guiada 4-4-4-4   │
        │ • Botão SOS Crise 24h         │ │ • Sons noturnos para insônia  │
        │ • Chat com equipe médica      │ │ • Assinatura Aurora Plus      │
        └───────────────────────────────┘ └───────────────────────────────┘
```

---

## 📁 3. Estrutura de Arquivos

```
design_system/
├── assets/
│   └── images/
│       ├── logo.png              # Logotipo oficial Aurora Elo
│       ├── clinic-hero.jpg       # Foto ambientada da clínica
│       ├── clinic-room.jpg       # Sala de acolhimento e terapia
│       ├── doctor-male.jpg       # Avatar de médico psiquiatra
│       ├── doctor-female.jpg     # Avatar de médica psiquiatra
│       ├── patient-1.jpg..4.jpg  # Fotos de pacientes para tabelas e cards
│       ├── mindfulness-bg.jpg    # Fundo sereno de montanhas e aurora
│       └── aurora-ambient.jpg    # Textura luminosa da aurora
├── css/
│   ├── tokens.css                # Tokens Tailwind CSS v4 (@theme & CSS vars)
│   └── custom.css                # Micro-interações, máscaras, frames mobile
├── js/
│   ├── i18n.js                   # Dicionário dinâmico PT-BR, EN e ES
│   ├── masks.js                  # Engine de máscaras (CPF, Fone, Data, Moeda, etc.)
│   └── app.js                    # Controlador interativo do showcase
├── components/
│   ├── buttons.html              # Botões clínicos, de teleconsulta e SOS
│   ├── inputs.html               # Todos os inputs com máscaras e validação
│   ├── cards.html                # Cards de métricas, pacientes e teleconsulta
│   ├── navigation.html           # Menus Vertical (Sidebar) e Horizontal (Topbar)
│   ├── tables.html               # Tabela de pacientes responsiva e filtrável
│   └── modals.html               # Modais de emergência e telemedicina
├── index.html                    # Showcase Mestre Interativo do Design System
├── login.html                    # Tela de Login Completa da Clínica
├── mobile-connected.html         # Simulador do App Mobile 1 (Conectado)
├── mobile-b2c.html               # Simulador do App Mobile 2 (Aurora Mind B2C)
├── tailwind.config.js            # Configuração oficial do Tailwind CSS
├── package.json                  # Scripts e dependências
└── README.md                     # Documentação completa
```

---

## 🎨 4. Design Tokens (Tailwind CSS v4)

No arquivo [`tokens.css`](file:///mnt/2c8d19a3-3bbb-4f90-b09f-9e17c780ce6a/Projects/auroraelo/design_system/css/tokens.css):

```css
@theme {
  --color-aurora-900: #0a2540;
  --color-aurora-600: #0284c7;
  --color-elo-500: #06b6d4;
  --color-healing-500: #10b981;
  --color-alert-500: #f59e0b;
  --color-crisis-500: #f43f5e;
  --color-zen-500: #8b5cf6;

  --font-sans: 'Plus Jakarta Sans', 'Inter', sans-serif;
  --font-display: 'Outfit', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

---

## ⌨️ 5. Máscaras e Placeholders de Todos os Tipos

O motor de máscaras [`masks.js`](file:///mnt/2c8d19a3-3bbb-4f90-b09f-9e17c780ce6a/Projects/auroraelo/design_system/js/masks.js) formata automaticamente os campos conforme o usuário digita:

| Campo | Máscara Aplicada | Exemplo de Placeholder |
| :--- | :--- | :--- |
| **CPF** | `000.000.000-00` | `000.000.000-00` |
| **Telefone / Celular** | `(00) 00000-0000` | `(11) 98765-4321` |
| **Data de Nascimento** | `DD/MM/AAAA` | `DD/MM/AAAA` |
| **Horário da Sessão** | `HH:mm` | `14:30` |
| **Valor da Consulta** | `R$ 0,00` ou `$ 0.00` | `R$ 450,00` |
| **CEP / Código Postal** | `00000-000` | `01310-100` |
| **Código do Prontuário** | `PRON-YYYY-0000` | `PRON-2026-0842` |
| **Cartão SUS (CNS)** | `000 0000 0000 0000` | `741 2045 8921 0004` |
| **Código 2FA (OTP)** | `_ _ _ _ _ _` (6 caixas com avanço automático) | Digite 1 dígito por caixa |
| **Senha com Força** | Barra dinâmica de 4 níveis | Medição em tempo real |
| **Slider Analógico** | Escala 0 a 10 com badge colorido | `4/10 • Ansiedade Leve` |

---

## 🌐 6. Suporte Multi-idioma (i18n)

Implementado em [`i18n.js`](file:///mnt/2c8d19a3-3bbb-4f90-b09f-9e17c780ce6a/Projects/auroraelo/design_system/js/i18n.js):
- 🇧🇷 **Português (Brasil)**
- 🇺🇸 **Inglês (English)**
- 🇪🇸 **Espanhol (Español)**

O seletor de idioma atualiza instantaneamente todos os rótulos, botões, cabeçalhos de tabela, menus e mensagens de crise sem recarregar a página.

---

## 🚀 7. Como Executar e Testar

### Modo Direto (Sem Dependências):
Basta abrir o arquivo [`index.html`](file:///mnt/2c8d19a3-3bbb-4f90-b09f-9e17c780ce6a/Projects/auroraelo/design_system/index.html) diretamente em qualquer navegador moderno.

### Modo Servidor Local:
```bash
cd design_system
npx serve . -l 3000
# Acesse http://localhost:3000
```
