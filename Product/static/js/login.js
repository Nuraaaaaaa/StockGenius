// ===== Login Page Script =====

// elements
const passwordInput = document.getElementById("password");
const toggleBtn = document.getElementById("togglePassword");
const form = document.getElementById("loginForm");
const toast = document.getElementById("toast");

// password visibility
toggleBtn.addEventListener("click", () => {
  passwordInput.type = passwordInput.type === "password" ? "text" : "password";
});

// login submit
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    alert("Please enter email and password");
    return;
  }

  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.message || "Invalid email or password");
      return;
    }

    // success
    toast.classList.remove("hidden");

    setTimeout(() => {
      window.location.href = "/dashboard";
    }, 700);

  } catch (err) {
    console.error(err);
    alert("Server error. Make sure Flask is running.");
  }
});