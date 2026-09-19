(() => {
  "use strict";

  const root = document.documentElement;
  const safeStorageGet = (key) => {
    try {
      return localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  };
  const safeStorageSet = (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch (_error) {
      // Menu preference still applies for the current document.
    }
  };
  // The presentation is pinned to the light theme: the clinic login and shell
  // use a fixed visual identity with no user-facing theme switch.
  root.dataset.bsTheme = "light";
  root.dataset.theme = "light";
  root.style.colorScheme = "light";
  root.classList.remove("app-skin-dark");

  const applyBranding = () => {
    const primary = document.body.dataset.clinicPrimary;
    const secondary = document.body.dataset.clinicSecondary;
    if (primary) root.style.setProperty("--clinic-primary", primary);
    if (secondary) root.style.setProperty("--clinic-secondary", secondary);

    document.querySelectorAll("[data-brand-preview]").forEach((preview) => {
      const previewPrimary = preview.dataset.brandPreviewPrimary;
      const previewSecondary = preview.dataset.brandPreviewSecondary;
      if (previewPrimary) preview.style.setProperty("--preview-primary", previewPrimary);
      if (previewSecondary) preview.style.setProperty("--preview-secondary", previewSecondary);
    });
  };

  const focusableElements = (container) =>
    Array.from(
      container.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ).filter((element) => !element.hidden && element.offsetParent !== null);

  document.addEventListener("DOMContentLoaded", () => {
    applyBranding();

    document.querySelectorAll(".progress-bar[aria-valuenow]").forEach((bar) => {
      const val = bar.getAttribute("aria-valuenow");
      if (val !== null && !bar.style.width) {
        bar.style.width = `${val}%`;
      }
    });

    const openButton = document.querySelector("[data-sidebar-open]");
    const closeButton = document.querySelector("[data-sidebar-close]");
    const sidebar = document.querySelector("[data-mobile-sidebar]");
    const overlay = document.querySelector("[data-sidebar-overlay]");

    const desktopLayout = window.matchMedia("(min-width: 1200px)");
    const backgroundRegions = [document.querySelector(".nxl-header"), document.querySelector(".nxl-container")];
    const closeSidebar = (restoreFocus = true) => {
      if (!sidebar) return;
      const wasOpen = sidebar.classList.contains("mob-navigation-active");
      sidebar.classList.remove("mob-navigation-active");
      sidebar.removeAttribute("role");
      sidebar.removeAttribute("aria-modal");
      sidebar.inert = !desktopLayout.matches;
      backgroundRegions.forEach((region) => { if (region) region.inert = false; });
      if (overlay) overlay.hidden = true;
      openButton?.setAttribute("aria-expanded", "false");
      root.classList.remove("product-scroll-locked");
      if (wasOpen && restoreFocus && !desktopLayout.matches) openButton?.focus();
    };

    const openSidebar = () => {
      if (!sidebar || desktopLayout.matches) return;
      sidebar.classList.add("mob-navigation-active");
      sidebar.inert = false;
      sidebar.setAttribute("role", "dialog");
      sidebar.setAttribute("aria-modal", "true");
      backgroundRegions.forEach((region) => { if (region) region.inert = true; });
      if (overlay) overlay.hidden = false;
      openButton?.setAttribute("aria-expanded", "true");
      root.classList.add("product-scroll-locked");
      closeButton?.focus();
    };

    openButton?.addEventListener("click", openSidebar);
    closeButton?.addEventListener("click", () => closeSidebar());
    overlay?.addEventListener("click", () => closeSidebar());
    closeSidebar(false);
    document.addEventListener("keydown", (event) => {
      if (!sidebar?.classList.contains("mob-navigation-active")) return;
      if (event.key === "Escape") { event.preventDefault(); closeSidebar(); }
      if (event.key !== "Tab") return;
      const focusable = focusableElements(sidebar);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    });

    const miniButton = document.getElementById("menu-mini-button");
    const expandButton = document.getElementById("menu-expend-button");
    const setNavigationExpanded = (item, expanded) => {
      item.classList.toggle("nxl-trigger", expanded);
      item.querySelector(":scope > button.nxl-link")?.setAttribute("aria-expanded", String(expanded));
      const submenu = item.querySelector(":scope > .nxl-submenu");
      if (submenu) submenu.hidden = !expanded;
    };
    let miniPreferred = safeStorageGet("nexel-classic-dashboard-menu-mini-theme") === "menu-mini-theme";
    const setMiniMenu = () => {
      const mini = miniPreferred && desktopLayout.matches;
      root.classList.toggle("minimenu", mini);
      if (mini) document.querySelectorAll(".nxl-hasmenu").forEach(item => setNavigationExpanded(item, false));
      if (miniButton) miniButton.style.display = mini ? "none" : "";
      if (expandButton) expandButton.style.display = mini ? "" : "none";
    };
    setMiniMenu();
    miniButton?.addEventListener("click", () => {
      miniPreferred = true; setMiniMenu();
      safeStorageSet("nexel-classic-dashboard-menu-mini-theme", "menu-mini-theme");
      expandButton?.focus();
    });
    expandButton?.addEventListener("click", () => {
      miniPreferred = false; setMiniMenu();
      safeStorageSet("nexel-classic-dashboard-menu-mini-theme", "menu-expend-theme");
      miniButton?.focus();
    });
    desktopLayout.addEventListener("change", () => {
      closeSidebar(false);
      setMiniMenu();
    });

    document.querySelectorAll("[data-copy-target]").forEach((button) => {
      button.addEventListener("click", async () => {
        const targetId = button.dataset.copyTarget;
        const target = targetId ? document.getElementById(targetId) : null;
        const status = button.parentElement?.querySelector("[data-copy-status]");
        if (!target || !status) return;
        try {
          await navigator.clipboard.writeText(target.textContent.trim());
          status.textContent = button.dataset.copySuccess || "";
        } catch (_error) {
          status.textContent = button.dataset.copyFailure || "";
        }
      });
    });

    // One controller owns visual, keyboard and accessibility accordion state.
    document.querySelectorAll(".nxl-navbar .nxl-hasmenu").forEach((item) => {
      const trigger = item.querySelector(":scope > button.nxl-link");
      const submenu = item.querySelector(":scope > .nxl-submenu");
      if (!trigger || !submenu) return;
      setNavigationExpanded(item, !root.classList.contains("minimenu") && Boolean(submenu.querySelector('[aria-current="page"]')));
      trigger.addEventListener("click", () => {
        if (root.classList.contains("minimenu")) {
          miniPreferred = false; setMiniMenu();
          safeStorageSet("nexel-classic-dashboard-menu-mini-theme", "menu-expend-theme");
        }
        setNavigationExpanded(item, trigger.getAttribute("aria-expanded") !== "true");
      });
    });
  });
})();
