# Aurora Elo - Quick Start Guide

## 🚀 Iniciar Rápido

### 1. Rodar Local
```bash
docker compose up -d
# Acesso: http://localhost:4132
```

### 2. Configurar Tunnel (Remoto)
```bash
cloudflared tunnel login
cloudflared tunnel create auroraelo
cloudflared tunnel run auroraelo
# Acesso: https://auroraelo.rgnsystems.com.br
```

### 3. Parar
```bash
docker compose down
```

## 📍 Endpoints

| Ambiente | URL | Descrição |
|----------|-----|-----------|
| Local | http://localhost:4132 | Desenvolvimento |
| Remoto | https://auroraelo.rgnsystems.com.br | Produção via Cloudflare |
| Health | http://localhost:4132/health/live/ | Status do servidor |
| Admin | http://localhost:4132/admin | Painel administrativo |

## 🎨 Recursos Novos

- ✅ Logo Aurora Elo em 4 versões WebP otimizadas
- ✅ Favicon SVG responsivo
- ✅ Suporte a 3 idiomas (pt-br, en, es)
- ✅ Sidebar expansível/retrátil
- ✅ Template home com nova estrutura

## 📂 Arquivos Criados

```
static/images/
├── aurora-elo-logo.webp          (Logo completo)
├── aurora-elo-login.webp         (Para login)
├── aurora-elo-sidebar-full.webp  (Sidebar estendido)
├── aurora-elo-sidebar-collapsed.webp (Sidebar recolhido)
└── favicon.svg                    (Favicon)

templates/workspace/
└── home-aurora-elo.html          (Novo template com sidebar)

Documentação/
├── AURORA_ELO_CONFIG.md          (Configuração completa)
├── AURORA_ELO_IMAGES.md          (Guia das imagens)
├── CLOUDFLARED_SETUP.md          (Setup do tunnel)
└── README.md (este arquivo)
```

## ⚙️ Configurações Importantes

```env
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,localhost:4132,auroraelo.rgnsystems.com.br
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:4132,https://auroraelo.rgnsystems.com.br
WEB_PORT=4132
LANGUAGE_CODE=pt-br
LANGUAGES=(pt-br, en, es)
```

## 🔍 Verificar Status

```bash
# Logs do servidor
docker compose logs web -f

# Health check
curl http://localhost:4132/health/live/

# Informações dos containers
docker compose ps
```

## 📞 Troubleshooting

| Problema | Solução |
|----------|---------|
| Porta 4132 em uso | `lsof -i :4132` depois `kill -9 <PID>` |
| Django não carrega | Verificar logs: `docker compose logs web` |
| Tunnel não conecta | `cloudflared tunnel status auroraelo` |
| Reiniciar tudo | `docker compose restart` |

## 📚 Documentação Completa

- **[AURORA_ELO_CONFIG.md](./AURORA_ELO_CONFIG.md)** - Configuração detalhada
- **[AURORA_ELO_IMAGES.md](./AURORA_ELO_IMAGES.md)** - Guia de uso das imagens
- **[CLOUDFLARED_SETUP.md](./CLOUDFLARED_SETUP.md)** - Setup do tunnel Cloudflare
- **[AURORA_ELO_CONFIG.md](./.cloudflared-config-example.yaml)** - Exemplo Cloudflared

## 🎯 Próximos Passos

1. ✅ Projeto renomeado para Aurora Elo
2. ✅ Imagens otimizadas em WebP
3. ✅ Favicon criado
4. ✅ Idiomas configurados
5. ✅ Aplicação rodando em localhost:4132
6. ⬜ Configurar Cloudflared tunnel (manual)
7. ⬜ Testar acesso remoto
8. ⬜ Implementar novo design system se necessário

## 🌐 Acesso Atualmente

```
Local: http://localhost:4132
Status: ✅ Ativo

Remoto: https://auroraelo.rgnsystems.com.br  
Status: ⏳ Aguardando configuração do Cloudflared
```

## 🔐 Segurança

- ✅ CSRF Protection
- ✅ SSL/TLS (via Cloudflare)
- ✅ MFA habilitado
- ✅ Isolamento de dados por clínica
- ✅ Auditoria de ações

---

**Versão**: Aurora Elo 1.0  
**Data**: 16 de Setembro de 2026  
**Status**: ✅ Pronto para Desenvolvimento
