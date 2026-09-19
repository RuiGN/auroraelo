(() => {
  "use strict";
  const focusKey = "mindcare:language-focus";

  document.addEventListener("DOMContentLoaded", () => {
    const forms = Array.from(document.forms).filter(form =>
      !form.hasAttribute("data-language-form") && form.method.toLowerCase() === "post",
    );
    const dirtyForms = new Set();
    forms.forEach(form => {
      const markDirty = () => dirtyForms.add(form);
      form.addEventListener("input", markDirty);
      form.addEventListener("change", markDirty);
      form.addEventListener("submit", () => dirtyForms.delete(form));
    });

    document.querySelectorAll("[data-language-form]").forEach(form => {
      form.addEventListener("submit", event => {
        if (dirtyForms.size && !window.confirm(form.dataset.languageConfirm)) {
          event.preventDefault();
          return;
        }
        dirtyForms.clear();
        // Existing form guards must not prompt a second time during this reload.
        window.dispatchEvent(new Event("mindcare:language-change"));
        try {
          sessionStorage.setItem(focusKey, form.dataset.languageSource);
        } catch (_error) {
          // Preference persistence is server-owned; storage is only for focus.
        }
      });
    });

    try {
      const source = sessionStorage.getItem(focusKey);
      sessionStorage.removeItem(focusKey);
      if (source) {
        queueMicrotask(() => document.getElementById(`${source}-language-toggle`)?.focus());
      }
    } catch (_error) {
      // Blocked browser storage does not prevent the language change.
    }
  });
})();
