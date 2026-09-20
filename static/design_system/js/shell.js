"use strict";
// Navegação apenas: sem tradução de relatos, chamadas clínicas ou telemetria.
document.addEventListener("DOMContentLoaded", () => {
  const portal = document.querySelector("[data-aurora-portal]");
  if (!portal) return;
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
});
