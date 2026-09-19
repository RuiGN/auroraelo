# Aurora Elo - Configuração e Documentação

## Visão Geral
Aurora Elo é uma plataforma de saúde mental integrada, construída com Django e servida através de um tunnel Cloudflared para acesso remoto seguro.

## Requisitos
- Docker e Docker Compose
- Cloudflared CLI
- Python 3.11+
- Variáveis de ambiente configuradas (.env)

## Configuração Local

### Portas
- **Local**: `http://localhost:4132`
- **Remoto**: `https://auroraelo.rgnsystems.com.br`
- **Banco de dados**: PostgreSQL 17 (porta 5432 - interno)
- **Cache**: Redis 8 (porta 6379 - interno)

### Iniciar o projeto
```bash
docker compose up -d
```

### Parar o projeto
```bash
docker compose down
```

## Suporte a Idiomas
Aurora Elo suporta 3 idiomas:
- **Português Brasileiro** (pt-br) - Padrão
- **Inglês** (en)
- **Espanhol** (es)

Os textos são traduzidos automaticamente via Django i18n.

## Imagens do Projeto

### WebP Otimizadas
- `aurora-elo-logo.webp` - Logo completo com fundo transparente
- `aurora-elo-login.webp` - Logo para tela de login (300x300px)
- `aurora-elo-sidebar-full.webp` - Logo para sidebar estendido (120x120px)
- `aurora-elo-sidebar-collapsed.webp` - Logo para sidebar recolhido (60x60px)

### Favicon
- `favicon.svg` - Ícone vetorial responsivo

## Tunnel Cloudflared

### Configurar o tunnel
```bash
cloudflared tunnel login
cloudflared tunnel create auroraelo
```

### Configuração do tunnel (config.yaml)
```yaml
tunnel: auroraelo
credentials-file: /Users/USERNAME/.cloudflared/auroraelo.json

ingress:
  - hostname: auroraelo.rgnsystems.com.br
    service: http://localhost:4132
  - service: http_status:404
```

### Iniciar o tunnel
```bash
cloudflared tunnel run auroraelo
```

## Autenticação e Segurança
- CSRF Protection habilitado
- SSL Redirect desabilitado em desenvolvimento
- MFA obrigatório (configurável)
- Suporte a múltiplas clínicas com isolamento de dados

## Estrutura de Dados
- **Apps Django**: accounts, clinics, people, journal, goals, scheduling, finance, analytics, wellness
- **Banco de dados**: PostgreSQL 17
- **Cache**: Redis 8 para sessões e cache de aplicação

## Variáveis de Ambiente Importantes
```
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,localhost:4132,auroraelo.rgnsystems.com.br
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:4132,https://auroraelo.rgnsystems.com.br
WEB_PORT=4132
DJANGO_TIME_ZONE=America/Sao_Paulo
```

## Templates
- Login/Autenticação: `/templates/accounts/auth_base.html`
- Workspace: `/templates/workspace/home.html`
- Design System: `/design_system_duralux/index.html`

## Logs
```bash
docker compose logs web -f
docker compose logs db -f
docker compose logs redis -f
```

## Troubleshooting

### Porta 4132 já em uso
```bash
lsof -i :4132
kill -9 <PID>
```

### Reiniciar containers
```bash
docker compose restart
```

### Reconstruir imagem
```bash
docker compose up -d --build
```

## Links Úteis
- Local: http://localhost:4132
- Remoto: https://auroraelo.rgnsystems.com.br
- Admin: http://localhost:4132/admin
- Health Check: http://localhost:4132/health/live/
