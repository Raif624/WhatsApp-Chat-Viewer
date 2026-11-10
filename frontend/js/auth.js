
// ==========================================
// WHATSAPP CHAT VIEWER - AUTHENTICATION
// ==========================================


const supabaseClient = window.supabaseClient;
// HTML elements
const authForm = document.getElementById("authForm");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");

const googleBtn = document.getElementById("googleBtn");
const magicLinkBtn = document.getElementById("magicLinkBtn");
const submitBtn = document.getElementById("submitBtn");

const switchModeBtn = document.getElementById("switchModeBtn");
const switchLabel = document.getElementById("switchLabel");
const statusMessage = document.getElementById("status");

// Authentication mode
let isRegisterMode = false;

// Redirect destination after authentication
const APP_URL = `${window.location.origin}/frontend/index.html`;


// ==========================================
// 1. DISPLAY STATUS MESSAGES
// ==========================================

function showStatus(message, isError = false) {
    statusMessage.textContent = message;

    statusMessage.style.color = isError
        ? "#dc2626"
        : "#087f5b";
}


// ==========================================
// 2. GOOGLE SIGN-IN
// ==========================================

googleBtn.addEventListener("click", async () => {
    try {
        googleBtn.disabled = true;
        showStatus("Connecting to Google...");

        const { error } = await supabaseClient.auth.signInWithOAuth({
            provider: "google",
            options: {
                redirectTo: APP_URL
            }
        });

        if (error) {
            throw error;
        }

    } catch (error) {
        showStatus(error.message, true);
        googleBtn.disabled = false;
    }
});


// ==========================================
// 3. SWITCH LOGIN / REGISTER MODE
// ==========================================

switchModeBtn.addEventListener("click", () => {
    isRegisterMode = !isRegisterMode;

    if (isRegisterMode) {
        submitBtn.textContent = "Create account";
        switchLabel.textContent = "Already have an account?";
        switchModeBtn.textContent = "Sign in";
        passwordInput.autocomplete = "new-password";
    } else {
        submitBtn.textContent = "Sign in";
        switchLabel.textContent = "New user?";
        switchModeBtn.textContent = "Create account";
        passwordInput.autocomplete = "current-password";
    }

    showStatus("");
});


// ==========================================
// 4. EMAIL + PASSWORD AUTHENTICATION
// ==========================================

authForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
        showStatus("Please enter your email and password.", true);
        return;
    }

    try {
        submitBtn.disabled = true;

        if (isRegisterMode) {

            showStatus("Creating your account...");

            const { data, error } = await supabaseClient.auth.signUp({
                email,
                password,
                options: {
                    emailRedirectTo: APP_URL
                }
            });

            if (error) {
                throw error;
            }

            if (data.session) {
                showStatus("Account created successfully.");
                window.location.assign(APP_URL);
            } else {
                showStatus(
                    "Registration successful! Check your email and confirm your account before signing in."
                );
            }

        } else {

            showStatus("Signing in...");

            const { error } = await supabaseClient.auth.signInWithPassword({
                email,
                password
            });

            if (error) {
                throw error;
            }

            showStatus("Login successful!");

            window.location.assign(APP_URL);
        }

    } catch (error) {
        showStatus(error.message, true);

    } finally {
        submitBtn.disabled = false;
    }
});


// ==========================================
// 5. PASSWORDLESS EMAIL MAGIC LINK
// ==========================================

magicLinkBtn.addEventListener("click", async () => {
    const email = emailInput.value.trim();

    if (!email) {
        showStatus("Enter your email address first.", true);
        emailInput.focus();
        return;
    }

    try {
        magicLinkBtn.disabled = true;
        showStatus("Sending your sign-in link...");

        const { error } = await supabaseClient.auth.signInWithOtp({
            email,
            options: {
                emailRedirectTo: APP_URL,
                shouldCreateUser: true
            }
        });

        if (error) {
            throw error;
        }

        showStatus("Check your email for your sign-in link.");

    } catch (error) {
        showStatus(error.message, true);

    } finally {
        magicLinkBtn.disabled = false;
    }
});


// ==========================================
// 6. CHECK EXISTING SESSION
// ==========================================

async function checkExistingSession() {
    const { data, error } = await supabaseClient.auth.getSession();

    if (error) {
        showStatus(error.message, true);
        return;
    }

    if (data.session) {
        window.location.replace(APP_URL);
    }
}

checkExistingSession();

console.log("Authentication page initialized.");
