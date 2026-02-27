const passwordInput = document.getElementById("password");
const confirmInput = document.getElementById("confirmPassword");
const matchHint = document.getElementById("matchHint");
const toggleBtn = document.getElementById("togglePassword");
const form = document.getElementById("signupForm");
const toast = document.getElementById("toast");
const submitBtn = document.getElementById("submitBtn");

// show/hide password
toggleBtn.addEventListener("click", () => {
    passwordInput.type =
        passwordInput.type === "password" ? "text" : "password";
});

// password match validation
function checkMatch() {
    const p = passwordInput.value;
    const c = confirmInput.value;

    if (c && p !== c) {
        matchHint.textContent = "Passwords do not match.";
        matchHint.className = "mt-1 text-[11px] text-red-500";
        submitBtn.disabled = true;
    } else {
        matchHint.textContent = "";
        submitBtn.disabled = false;
    }
}

passwordInput.addEventListener("input", checkMatch);
confirmInput.addEventListener("input", checkMatch);

// SUBMIT → send to Flask
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (passwordInput.value !== confirmInput.value) {
        matchHint.textContent = "Passwords do not match.";
        return;
    }

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = passwordInput.value;

    try {
        const res = await fetch("/api/signup", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ name, email, password })
        });

        const data = await res.json();

        if (!res.ok) {
            matchHint.textContent = data.message;
            matchHint.className = "mt-1 text-[11px] text-red-500";
            return;
        }

        // success
        toast.classList.remove("hidden");

        setTimeout(() => {
            window.location.href = "/login";
        }, 900);

    } catch (err) {
        console.error(err);
        matchHint.textContent = "Server error.";
    }
});