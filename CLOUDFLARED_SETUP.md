# Guia: Configurar Tunnel Cloudflared para Aurora Elo

## Pré-requisitos
- Conta Cloudflare
- Domínio `auroraelo.rgnsystems.com.br` configurado em Cloudflare
- Cloudflared CLI instalado ([download](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/))

## Passo 1: Fazer Login no Cloudflare

```bash
cloudflared tunnel login
```

Isso abrirá uma página web para autenticar. Escolha o domínio `rgnsystems.com.br` quando solicitado.

## Passo 2: Criar o Tunnel

```bash
cloudflared tunnel create auroraelo
```

Você receberá uma credencial JSON que será salva em:
```
~/.cloudflared/auroraelo.json
```

## Passo 3: Criar o Arquivo de Configuração

Copie o arquivo `.cloudflared-config-example.yaml` para a sua home Cloudflare:

```bash
cp .cloudflared-config-example.yaml ~/.cloudflared/config.yaml
```

**Ou edite manualmente:**

```yaml
tunnel: auroraelo
credentials-file: /Users/USERNAME/.cloudflared/auroraelo.json

ingress:
  - hostname: auroraelo.rgnsystems.com.br
    service: http://localhost:4132
  - service: http_status:404
```

Substitua `USERNAME` pelo seu usuário do macOS/Linux.

## Passo 4: Registrar o DNS no Cloudflare

Acesse o painel Cloudflare e vá para DNS Records:

1. Crie um registro CNAME:
   - Name: `auroraelo`
   - Target: `auroraelo.rgnsystems.com.br.cfargotunnel.com`
   - TTL: Auto
   - Proxy: Proxied (laranja)

Ou execute automaticamente:

```bash
cloudflared tunnel route dns auroraelo auroraelo.rgnsystems.com.br
```

## Passo 5: Iniciar o Tunnel

```bash
cloudflared tunnel run auroraelo
```

Você verá uma mensagem como:
```
2026-09-16T14:30:00Z INF Registered tunnel connection connIndex=0 connection=abc123 attempt=1
2026-09-16T14:30:00Z INF You can now visit your tunnel at: https://auroraelo.rgnsystems.com.br
```

## Passo 6: Manter o Tunnel Sempre Online (Optional)

### macOS - Criar Serviço Automático

```bash
sudo cloudflared service install
sudo launchctl start com.cloudflare.cloudflared
```

### Linux - Usar Systemd

```bash
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

### Em Produção - Docker

Adicione ao `docker-compose.yml`:

```yaml
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: aurora-elo-tunnel
    restart: always
    command: tunnel run
    environment:
      TUNNEL_TOKEN: <seu-token-aqui>
```

## Verificação

Teste o acesso:

1. **Local**:
   ```bash
   curl http://localhost:4132/health/live/
   ```

2. **Remoto**:
   ```bash
   curl https://auroraelo.rgnsystems.com.br/health/live/
   ```

## Troubleshooting

### Tunnel não está rodando

```bash
cloudflared tunnel status auroraelo
```

### Limpar credenciais antigas

```bash
rm ~/.cloudflared/auroraelo.json
cloudflared tunnel delete auroraelo
# Refaça os passos 1-4
```

### Verificar logs

```bash
tail -f ~/.cloudflared/auroraelo.log
```

## Variáveis de Ambiente para Docker

Se usar Docker para o tunnel:

```bash
export TUNNEL_TOKEN=$(cat ~/.cloudflared/auroraelo.json | jq -r '.TunnelToken')
docker run -d \
  --name aurora-elo-tunnel \
  --restart always \
  -e TUNNEL_TOKEN=$TUNNEL_TOKEN \
  cloudflare/cloudflared:latest \
  tunnel run
```

## Monitoramento

Acesse o painel Cloudflare para ver:
- Atividade do túnel
- Estatísticas de banda
- Analytics de requisições

URL: `https://dash.cloudflare.com` → Selecione domínio → Traffic → Tunnels

---

**Documentação oficial**: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
