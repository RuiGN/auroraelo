"use strict";

(function () {
  function initMasterNavigation() {
    const sidebar = document.querySelector("[data-master-sidebar]");
    const toggle = document.querySelector("[data-master-menu-toggle]");
    const close = document.querySelector("[data-master-menu-close]");

    if (!sidebar || !toggle) return;

    const firstLink = sidebar.querySelector("a");

    function setOpen(open, restoreFocus) {
      sidebar.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));

      if (open && firstLink) {
        firstLink.focus();
      } else if (!open && restoreFocus) {
        toggle.focus();
      }
    }

    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true", true);
    });

    if (close) {
      close.addEventListener("click", function () {
        setOpen(false, true);
      });
    }

    sidebar.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.matchMedia("(max-width: 1199.98px)").matches) {
          setOpen(false, false);
        }
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
        event.preventDefault();
        setOpen(false, true);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMasterNavigation);
  } else {
    initMasterNavigation();
  }
})();
