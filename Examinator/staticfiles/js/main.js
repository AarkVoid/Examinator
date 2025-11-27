// -------------------------------
// GLOBAL SCRIPT.JS
// -------------------------------

// ========== NAVBAR TOGGLE ==========
document.addEventListener("DOMContentLoaded", () => {
  const navToggle = document.querySelector("#nav-toggle");
  const navLinks = document.querySelector(".nav-links");

  if (navToggle && navLinks) {
    navToggle.addEventListener("change", () => {
      navLinks.classList.toggle("active", navToggle.checked);
    });
  }

  // ========== SIDEBAR TOGGLE ==========
  const sidebarToggle = document.querySelector("#sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("change", () => {
      sidebar.classList.toggle("open", sidebarToggle.checked);
    });
  }

  // ========== DROPDOWNS ==========
  document.querySelectorAll(".dropdown").forEach((dropdown) => {
    const toggle = dropdown.querySelector(".dropdown-toggle");
    if (toggle) {
      toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.classList.toggle("open");
      });
    }
  });
  document.addEventListener("click", () => {
    document.querySelectorAll(".dropdown.open").forEach((d) => d.classList.remove("open"));
  });

  // ========== TABS ==========
  document.querySelectorAll("[data-tab]").forEach((tabBtn) => {
    tabBtn.addEventListener("click", () => {
      const target = tabBtn.dataset.tab;

      document.querySelectorAll(".tab-content").forEach((c) =>
        c.classList.remove("active")
      );
      document.querySelector(`#${target}`)?.classList.add("active");

      document.querySelectorAll("[data-tab]").forEach((b) =>
        b.classList.remove("active")
      );
      tabBtn.classList.add("active");
    });
  });

  // ========== MODALS ==========
  document.querySelectorAll("[data-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.modal;
      document.querySelector(`#${target}`)?.classList.add("open");
    });
  });
  document.querySelectorAll(".modal .close").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".modal").classList.remove("open");
    });
  });

  // ========== TOAST NOTIFICATIONS ==========
  function showToast(message, type = "info", timeout = 3000) {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerText = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add("show"), 50);
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, timeout);
  }
  window.showToast = showToast;

  // Example: showToast("Welcome back!", "success");

  // ========== FORM VALIDATION ==========
  document.querySelectorAll("form.validate").forEach((form) => {
    form.addEventListener("submit", (e) => {
      let valid = true;
      form.querySelectorAll("[required]").forEach((input) => {
        if (!input.value.trim()) {
          valid = false;
          input.classList.add("error");
          input.nextElementSibling?.classList.add("show");
        } else {
          input.classList.remove("error");
          input.nextElementSibling?.classList.remove("show");
        }
      });
      if (!valid) e.preventDefault();
    });
  });

  // ========== COLLAPSIBLES ==========
  document.querySelectorAll(".collapsible .toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".collapsible").classList.toggle("open");
    });
  });

  // ========== DARK MODE ==========
  const darkToggle = document.querySelector("#dark-mode-toggle");
  if (darkToggle) {
    darkToggle.addEventListener("click", () => {
      document.body.classList.toggle("dark");
      localStorage.setItem(
        "darkMode",
        document.body.classList.contains("dark") ? "1" : "0"
      );
    });

    if (localStorage.getItem("darkMode") === "1") {
      document.body.classList.add("dark");
    }
  }

  // ========== CHAT AUTOSCROLL ==========
  const chatBox = document.querySelector(".chat-messages");
  if (chatBox) {
    chatBox.scrollTop = chatBox.scrollHeight;
  }
});
