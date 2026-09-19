(() => {
  "use strict";

  const initialSubmitState = new WeakMap();
  const initializedMasks = new WeakSet();

  const canonicalize = (input) => input.value.replace(/\D/g, "");

  const formatPhone = (digits) => {
    const value = digits.slice(0, 11);
    if (value.length <= 2) return value;
    if (value.length <= 6) return `(${value.slice(0, 2)}) ${value.slice(2)}`;
    if (value.length <= 10) {
      return `(${value.slice(0, 2)}) ${value.slice(2, 6)}-${value.slice(6)}`;
    }
    return `(${value.slice(0, 2)}) ${value.slice(2, 7)}-${value.slice(7)}`;
  };

  const formatDocument = (digits) => {
    const value = digits.slice(0, 14);
    if (value.length <= 11) {
      return value
        .replace(/^(\d{3})(\d)/, "$1.$2")
        .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
        .replace(/\.(\d{3})(\d)/, ".$1-$2");
    }
    return value
      .replace(/^(\d{2})(\d)/, "$1.$2")
      .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
      .replace(/\.(\d{3})(\d)/, ".$1/$2")
      .replace(/(\/\d{4})(\d)/, "$1-$2");
  };

  const maskFormats = {
    phone: { max: 11, format: formatPhone },
    document: { max: 14, format: formatDocument },
    cep: { max: 8, format: digits => digits.replace(/^(\d{5})(\d)/, "$1-$2") },
  };

  const canonicalValueFor = input => {
    const digits = canonicalize(input);
    // International phone numbers must never become truncated local numbers.
    return input.dataset.mask === "phone" && input.value.trim().startsWith("+")
      ? `+${digits}` : digits;
  };

  const initializeMasks = (form) => {
    if (initializedMasks.has(form)) return;
    initializedMasks.add(form);
    const maskedInputs = Array.from(form.querySelectorAll("input[data-mask]"))
      .filter(input => Object.hasOwn(maskFormats, input.dataset.mask));
    const updates = maskedInputs.map(input => {
      const updateMask = () => {
        const position = input.selectionStart;
        const before = input.value;
        const digitsBefore = before.slice(0, position ?? before.length).replace(/\D/g, "").length;
        const canonicalValue = canonicalValueFor(input);
        const config = maskFormats[input.dataset.mask];
        input.dataset.canonicalValue = canonicalValue;
        // Preserve invalid/overlong data for server validation; do not hide it.
        input.value = canonicalValue.startsWith("+") || canonicalValue.length > config.max
          ? canonicalValue : config.format(canonicalValue);
        if (document.activeElement === input && position !== null) {
          let caret = 0;
          let count = 0;
          while (caret < input.value.length && count < digitsBefore) {
            if (/\d/.test(input.value[caret])) count += 1;
            caret += 1;
          }
          input.setSelectionRange(caret, caret);
        }
      };
      input.addEventListener("input", updateMask);
      input.addEventListener("change", updateMask);
      updateMask();
      return updateMask;
    });
    form.addEventListener("submit", () => {
      maskedInputs.forEach(input => {
        const canonicalValue = canonicalValueFor(input);
        input.value = canonicalValue;
        input.dataset.canonicalValue = canonicalValue;
      });
    });
    form.addEventListener("reset", () => setTimeout(() => updates.forEach(update => update()), 0));
    window.addEventListener("pageshow", () => updates.forEach(update => update()));
  };

  const initializeForm = (form) => {
    let dirty = false;
    const submitButton = form.querySelector("[data-submit-button]");
    if (submitButton) initialSubmitState.set(submitButton, submitButton.disabled);

    form.addEventListener("input", () => { dirty = true; });
    form.addEventListener("change", () => { dirty = true; });
    window.addEventListener("mindcare:language-change", () => { dirty = false; });
    form.addEventListener("submit", (event) => {
      if (form.dataset.submitting === "true") {
        event.preventDefault();
        return;
      }
      form.setAttribute("data-submitting", "true");
      dirty = false;
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.setAttribute("aria-disabled", "true");
      }
    });

    form.querySelectorAll("[data-destructive-action]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        const accepted = window.confirm(button.dataset.confirmation);
        if (accepted) form.requestSubmit(button);
      });
    });

    window.addEventListener("beforeunload", (event) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = form.dataset.dirtyMessage;
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form").forEach(initializeMasks);
    document.querySelectorAll("[data-form-guard]").forEach(initializeForm);
    document.querySelectorAll("[data-brand-preview]").forEach((preview) => {
      const primary = document.querySelector("[data-brand-primary-input]");
      const secondary = document.querySelector("[data-brand-secondary-input]");
      const logo = document.querySelector("[data-brand-logo-input]");
      const previewLogo = preview.querySelector("[data-brand-preview-logo]");
      const updateColors = () => {
        if (primary?.value) preview.style.setProperty("--clinic-primary", primary.value);
        if (secondary?.value) preview.style.setProperty("--clinic-secondary", secondary.value);
      };
      primary?.addEventListener("input", updateColors);
      secondary?.addEventListener("input", updateColors);
      logo?.addEventListener("change", () => {
        const file = logo.files?.[0];
        if (!file || !previewLogo) return;
        previewLogo.src = URL.createObjectURL(file);
        previewLogo.classList.remove("hidden", "d-none");
      });
      updateColors();
    });
    const invalidField = Array.from(document.querySelectorAll(
      'input[aria-invalid="true"]:not([type="hidden"]), select[aria-invalid="true"], textarea[aria-invalid="true"]',
    )).find((field) => !field.disabled && field.getClientRects().length);
    (invalidField || document.querySelector("[data-focus-error-summary]"))?.focus();
  });

  window.addEventListener("pageshow", () => {
    document.querySelectorAll("[data-form-guard]").forEach((form) => {
      form.removeAttribute("data-submitting");
      const submitButton = form.querySelector("[data-submit-button]");
      if (submitButton) {
        submitButton.disabled = initialSubmitState.get(submitButton) ?? submitButton.disabled;
        if (submitButton.disabled) submitButton.setAttribute("aria-disabled", "true");
        else submitButton.removeAttribute("aria-disabled");
      }
    });
  });
})();
