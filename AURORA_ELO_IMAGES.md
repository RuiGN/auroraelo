# Guia de Uso: Imagens Aurora Elo

## Localização
Todas as imagens estão em:
```
/static/images/aurora-elo-*
/static/images/favicon.svg
```

## Imagens WebP

### 1. Logo Completo
**Arquivo**: `aurora-elo-logo.webp`
**Tamanho**: 300x300px
**Uso**: Home inicial, splash screen, apresentações
```html
<img src="{% static 'images/aurora-elo-logo.webp' %}" alt="Aurora Elo" width="300" height="300">
```

### 2. Logo Login
**Arquivo**: `aurora-elo-login.webp`
**Tamanho**: 300x300px
**Uso**: Tela de autenticação, recuperação de senha, registro
```html
<div class="auth-logo-container">
  <img src="{% static 'images/aurora-elo-login.webp' %}" alt="Aurora Elo" width="300" height="300">
</div>
```

### 3. Sidebar Estendido
**Arquivo**: `aurora-elo-sidebar-full.webp`
**Tamanho**: 120x120px
**Uso**: Logo na navegação lateral estendida
```html
<div class="sidebar-logo">
  <img src="{% static 'images/aurora-elo-sidebar-full.webp' %}" alt="Aurora Elo" width="120" height="120">
  <span>Aurora Elo</span>
</div>
```

### 4. Sidebar Recolhido
**Arquivo**: `aurora-elo-sidebar-collapsed.webp`
**Tamanho**: 60x60px
**Uso**: Logo compacto quando sidebar está minimizada
```html
<div class="sidebar-logo-collapsed">
  <img src="{% static 'images/aurora-elo-sidebar-collapsed.webp' %}" alt="Aurora Elo" width="60" height="60">
</div>
```

## Favicon SVG

**Arquivo**: `favicon.svg`
**Tamanho**: Escalável (SVG)
**Uso**: Ícone na aba do navegador
```html
<link rel="icon" href="{% static 'images/favicon.svg' %}" type="image/svg+xml">
```

## Exemplo Completo: Template com Sidebar Dinâmico

```html
{% load static %}
<!DOCTYPE html>
<html>
<head>
  <title>Aurora Elo</title>
  <link rel="icon" href="{% static 'images/favicon.svg' %}" type="image/svg+xml">
  <style>
    .sidebar { width: 250px; transition: width 0.3s; }
    .sidebar.collapsed { width: 80px; }
    .sidebar.collapsed .sidebar-text { display: none; }
  </style>
</head>
<body>
  <nav class="sidebar" id="sidebar">
    <div class="sidebar-logo" id="sidebar-logo">
      <img src="{% static 'images/aurora-elo-sidebar-full.webp' %}" alt="Aurora Elo" id="logo-img">
    </div>
    <!-- Resto da navegação -->
  </nav>

  <main>
    <h1>Aurora Elo Dashboard</h1>
  </main>

  <script>
    const sidebar = document.getElementById('sidebar');
    const logoImg = document.getElementById('logo-img');
    
    function toggleSidebar() {
      sidebar.classList.toggle('collapsed');
      if (sidebar.classList.contains('collapsed')) {
        logoImg.src = "{% static 'images/aurora-elo-sidebar-collapsed.webp' %}";
        logoImg.style.width = '60px';
        logoImg.style.height = '60px';
      } else {
        logoImg.src = "{% static 'images/aurora-elo-sidebar-full.webp' %}";
        logoImg.style.width = '120px';
        logoImg.style.height = '120px';
      }
    }
  </script>
</body>
</html>
```

## CSS Recomendado

```css
/* Sidebar Logo Container */
.sidebar-logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1rem;
  border-bottom: 1px solid #f0f0f0;
  height: 90px;
  transition: all 0.3s ease;
}

.sidebar-logo-container img {
  max-width: 100%;
  height: auto;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

/* Login Logo */
.auth-logo-container {
  display: flex;
  justify-content: center;
  margin-bottom: 2rem;
}

.auth-logo-container img {
  max-width: 300px;
  height: auto;
}

/* Brand Wordmark */
.product-wordmark {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 1.25rem;
  color: #1e5a96;
}

.product-wordmark img {
  width: 32px;
  height: 32px;
}
```

## Performance

Todas as imagens foram otimizadas em WebP para:
- **Logo completo**: 55KB (vs ~200KB em PNG)
- **Login**: 26KB (vs ~80KB em PNG)
- **Sidebar full**: 7.2KB (vs ~30KB em PNG)
- **Sidebar collapsed**: 2.6KB (vs ~15KB em PNG)

**Economia**: ~85% de redução no tamanho das imagens!

## Compatibilidade Navegadores

- ✅ WebP: Chrome 23+, Edge 18+, Firefox 65+, Safari 16+
- ✅ SVG: Todos os navegadores modernos
- ⚠️ Fallback: Use `<picture>` para navegadores antigos

```html
<picture>
  <source srcset="{% static 'images/aurora-elo-logo.webp' %}" type="image/webp">
  <img src="{% static 'images/aurora-elo-logo.png' %}" alt="Aurora Elo">
</picture>
```

## Variação de Tema (Futuro)

Você pode criar variações adicionais:
- `aurora-elo-dark.webp` - Para modo escuro
- `aurora-elo-light.webp` - Para modo claro
- `aurora-elo-compact.webp` - Para dispositivos móveis

Siga o mesmo processo de otimização WebP!

---

**Última atualização**: 16 de Setembro de 2026
**Versão**: Aurora Elo 1.0
