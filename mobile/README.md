# 📱 Ecossistema Mobile Aurora Elo

Este diretório contém a implementação dos **dois aplicativos mobile** que compõem o ecossistema Aurora Elo:

---

## 1. 🏥 App 1: `mobile/connected` (Aurora Elo Clínica Conectada)
* **Público:** Pacientes em acompanhamento psiquiátrico, acompanhantes/familiares e psiquiatras de plantão.
* **Conexão:** Sincronizado em tempo real com o prontuário eletrônico web (`/psiquiatria/api/v1/patient/`).
* **Recursos Principais:**
  - **Prontuário Móvel:** Acesso a laudos, diagnósticos CID-11 e prescrições digitais assinadas.
  - **Telepsiquiatria HD em 1 Toque:** Entrada direta na sala virtual criptografada (E2EE 256-bit).
  - **Checagem de Adesão Medicamentosa:** Checklist diário com horários e confirmação de dose tomada.
  - **Botão SOS Crise 24h:** Aciona geolocalização e notifica imediatamente o plantão médico da clínica e o responsável legal.
  - **Chat Seguro com a Equipe:** Comunicação direta com a equipe multiprofissional.

---

## 2. 🌿 App 2: `mobile/b2c` (Aurora Mind & Wellness - B2C Lojas de Apps)
* **Público:** Consumidores gerais, adeptos de autocuidado, meditação e psicoeducação (Google Play & Apple App Store).
* **Monetização:** Freemium + Assinatura *Aurora Mind Plus* (R$ 29,90/mês ou R$ 249,90/ano).
* **Recursos Principais:**
  - **Rastreador Diário de Humor:** Registro com valência afetiva, nível de energia e sono.
  - **Diário de Pensamentos TCC:** Reestruturação cognitiva de pensamentos automáticos e distorções cognitivas.
  - **Respiração Guiada 4-4-4-4 (Box Breathing):** Exercício clínico animado para alívio rápido de taquicardia e ansiedade.
  - **Paisagens Sonoras Noturnas:** Frequências binaurais e meditações para insônia.
  - **Exportação Médica:** Geração de relatório consolidado em PDF para apresentação ao médico psiquiatra.

---

## 🚀 Como Executar os Apps Mobiles

### App 1 (Clínico Conectado):
```bash
cd mobile/connected
npm install
npx expo start
```

### App 2 (Aurora Mind B2C):
```bash
cd mobile/b2c
npm install
npx expo start
```
