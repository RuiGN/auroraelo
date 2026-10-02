/* Aplica o tema salvo (claro/escuro) antes da primeira pintura, para não piscar.
   Arquivo externo porque a CSP do produto não permite <script> inline. */
try {
  var theme = localStorage.getItem('ae-theme');
  if (!theme && window.matchMedia) {
    theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  if (theme) document.documentElement.setAttribute('data-theme', theme);
} catch (e) { /* armazenamento indisponível: segue o tema do sistema */ }
