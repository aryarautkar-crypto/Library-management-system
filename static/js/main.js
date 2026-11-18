// Small helpers for the Library Management UI:
// theme toggle, show/hide password, register form check,
// confirm dialogs and auto-hiding messages.
document.addEventListener("DOMContentLoaded", function () {
  var root = document.documentElement;

  // ----- Light / dark theme toggle (the saved choice is applied in base.html) -----
  var toggle = document.getElementById("themeToggle");
  function toggleLabel() {
    return root.getAttribute("data-bs-theme") === "dark" ? "Switch to light theme" : "Switch to dark theme";
  }
  if (toggle) {
    toggle.setAttribute("aria-label", toggleLabel());
    toggle.setAttribute("title", toggleLabel());
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      toggle.setAttribute("aria-label", toggleLabel());
      toggle.setAttribute("title", toggleLabel());
    });
  }

  // ----- "Show password" checkbox -----
  var pwd = document.getElementById("password");
  var showPwd = document.getElementById("showPwd");
  if (pwd && showPwd) {
    showPwd.addEventListener("change", function () {
      pwd.type = showPwd.checked ? "text" : "password";
    });
  }

  // ----- Register form: check the password length before sending it to the server -----
  var registerForm = document.getElementById("registerForm");
  if (registerForm && pwd) {
    registerForm.addEventListener("submit", function (e) {
      if (pwd.value.length < 6) {
        e.preventDefault();
        alert("Password must be at least 6 characters.");
      }
    });
  }

  // ----- Success and info messages disappear after 5 seconds (errors stay) -----
  document.querySelectorAll(".alert-success, .alert-info").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity .4s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 450);
    }, 5000);
  });

  // ----- Any button or link with data-confirm="..." asks before it runs -----
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!confirm(el.getAttribute("data-confirm"))) {
        e.preventDefault();
      }
    });
  });
});
