// Chhota JavaScript: password dikhana/chhupana, form check, delete se pehle confirm
document.addEventListener("DOMContentLoaded", function () {
  var pwd = document.getElementById("password");
  var showPwd = document.getElementById("showPwd");

  // "Show password" checkbox
  if (pwd && showPwd) {
    showPwd.addEventListener("change", function () {
      pwd.type = showPwd.checked ? "text" : "password";
    });
  }

  // Register form: server par bhejne se pehle password length check
  var registerForm = document.getElementById("registerForm");
  if (registerForm && pwd) {
    registerForm.addEventListener("submit", function (e) {
      if (pwd.value.length < 6) {
        e.preventDefault();
        alert("Password kam se kam 6 characters ka hona chahiye.");
      }
    });
  }

  // Koi bhi button/link jisme data-confirm="..." ho, click par pehle puchega
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!confirm(el.getAttribute("data-confirm"))) {
        e.preventDefault();
      }
    });
  });
});
