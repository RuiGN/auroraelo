"use strict";
// Shell apenas: navegação, idioma e apresentação.
// Sem tradução de relatos, chamadas clínicas ou telemetria.

// Tema pinado no claro por padrão em toda a plataforma; sem alternância.
const root = document.documentElement;
try {
  root.dataset.bsTheme = "light";
} catch (error) {
  // Armazenamento indisponível: mantém o tema padrão claro.
}

// Acesso seguro ao armazenamento local com fallback silencioso.
function safeStorageGet(key, fallback) {
  try {
    const value = window.localStorage.getItem(key);
    return value === null ? fallback : value;
  } catch (error) {
    return fallback;
  }
}
function safeStorageSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch (error) {
    // Armazenamento indisponível: nenhuma persistência.
  }
}

function formIsDirty(scope) {
  const forms = scope ? scope.querySelectorAll("form[data-form-guard]") : document.querySelectorAll("form[data-form-guard]");
  for (const form of forms) {
    if (form.closest("[data-language-form]")) continue;
    for (const control of form.querySelectorAll("input, textarea, select")) {
      if (control.type === "hidden" || control.type === "submit") continue;
      if (control.defaultValue !== control.value) return true;
    }
  }
  return false;
}

document.addEventListener("DOMContentLoaded", () => {
  // --- Workspace: drawer e recolhimento da navegação lateral ---
  const workspace = document.querySelector(".aurora-workspace[data-sidebar-toggle]");
  if (workspace) {
    const sidebar = workspace.querySelector("[data-mobile-sidebar]");
    const overlay = workspace.querySelector("[data-sidebar-overlay]");
    const openButtons = workspace.querySelectorAll("[data-sidebar-open]");
    const closeButtons = workspace.querySelectorAll("[data-sidebar-close]");
    const miniButton = workspace.querySelector("[data-sidebar-mini]");
    const expandButton = workspace.querySelector("[data-sidebar-expand]");

    function setDrawer(open) {
      if (!sidebar || !overlay) return;
      sidebar.classList.toggle("is-open", open);
      overlay.hidden = !open;
      overlay.classList.toggle("d-none", !open);
      openButtons.forEach((button) => button.setAttribute("aria-expanded", String(open)));
    }
    function setMini(mini) {
      workspace.dataset.sidebar = mini ? "mini" : "expanded";
      if (miniButton) miniButton.style.display = mini ? "none" : "";
      if (expandButton) expandButton.style.display = mini ? "" : "none";
      safeStorageSet("aurora-sidebar-mini", mini ? "1" : "0");
    }

    if (safeStorageGet("aurora-sidebar-mini", "0") === "1") setMini(true);
    openButtons.forEach((button) => button.addEventListener("click", () => setDrawer(true)));
    closeButtons.forEach((button) => button.addEventListener("click", () => setDrawer(false)));
    if (overlay) overlay.addEventListener("click", () => setDrawer(false));
    if (miniButton) miniButton.addEventListener("click", () => setMini(true));
    if (expandButton) expandButton.addEventListener("click", () => setMini(false));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && sidebar && sidebar.classList.contains("is-open")) {
        setDrawer(false);
      }
    });
  }

  // --- Login: seletor de perfil ajusta o placeholder do identificador ---
  const roleTabs = document.querySelectorAll("[data-role-tab]");
  if (roleTabs.length) {
    const identifier = document.querySelector("input[name='email'], input[type='text'][autocomplete='email'], input[type='text']");
    roleTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        roleTabs.forEach((item) => item.classList.toggle("is-active", item === tab));
        if (identifier) identifier.placeholder = tab.dataset.rolePlaceholder || identifier.placeholder;
      });
    });
  }

  // --- Login: mostrar/ocultar senha ---
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const control = button.parentElement.querySelector("input[type='password'], input[type='text']");
      if (!control) return;
      const revealing = control.type === "password";
      control.type = revealing ? "text" : "password";
      button.setAttribute("aria-label", revealing ? "Ocultar senha" : "Mostrar senha");
    });
  });

  // --- Idioma: submissão pelo servidor, com confirmação em formulários sujos ---
  document.querySelectorAll("[data-language-form]").forEach((form) => {
    const select = form.querySelector("select[name='language']");
    if (!select) return;
    select.addEventListener("change", () => {
      const confirmMessage = form.dataset.languageConfirm;
      if (confirmMessage && formIsDirty(form.closest("body") || document)) {
        if (!window.confirm(confirmMessage)) {
          select.value = select.querySelector("option[selected]") ? select.querySelector("option[selected]").value : select.value;
          return;
        }
      }
      form.submit();
    });
  });

  // --- Foco no resumo de erros quando presente ---
  const errorSummary = document.querySelector("[data-focus-error-summary]");
  if (errorSummary) errorSummary.focus();

  // --- Portal de psiquiatria: navegação e layout ---
  const portal = document.querySelector("[data-aurora-portal]");
  if (portal) {
    const toggle = portal.querySelector("[data-aurora-nav-toggle]");
    const navigation = document.getElementById("psychiatry-navigation");
    const mobile = window.matchMedia("(max-width: 767px)");
    function setOpen(open) {
      navigation.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
    }
    function resize() { setOpen(!mobile.matches); }
    toggle.addEventListener("click", () => setOpen(navigation.hidden));
    portal.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && mobile.matches && !navigation.hidden) {
        setOpen(false);
        toggle.focus();
      }
    });
    mobile.addEventListener("change", resize);
    resize();
    portal.querySelectorAll("[data-aurora-layout]").forEach((button) => {
      button.addEventListener("click", () => {
        portal.dataset.layout = button.dataset.auroraLayout;
        portal.querySelectorAll("[data-aurora-layout]").forEach((control) => {
          control.setAttribute("aria-pressed", String(control === button));
        });
      });
    });
  }
});
