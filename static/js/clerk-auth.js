
(() => {
    "use strict";

    const statusElement = document.getElementById("auth-status");
    const signInButton = document.getElementById("sign-in-button");
    const signUpButton = document.getElementById("sign-up-button");
    const userButtonContainer = document.getElementById("user-button");

    const profileSection = document.getElementById("profile-setup");
    const profileForm = document.getElementById("profile-form");
    const universitySelect = document.getElementById("university");
    const otherUniversityContainer = document.getElementById(
        "other-university-container"
    );
    const otherUniversityInput = document.getElementById("other-university");
    const saveProfileButton = document.getElementById("save-profile-button");
    const profileMessage = document.getElementById("profile-message");

    function showSignedOut() {
        statusElement.textContent = "Not signed in";
        signInButton.hidden = false;
        signUpButton.hidden = false;
        userButtonContainer.hidden = true;

        if (profileSection) {
            profileSection.hidden = true;
        }
    }

    function showSignedIn(user) {
        const firstName = user?.firstName?.trim();
        const email = user?.primaryEmailAddress?.emailAddress;
        const label = firstName || email || "Signed in";

        statusElement.textContent = `Welcome, ${label}`;
        signInButton.hidden = true;
        signUpButton.hidden = true;
        userButtonContainer.hidden = false;
    }

    async function getSessionToken() {
        if (!window.Clerk?.session) {
            throw new Error("Your session is not ready. Please try again.");
        }

        const token = await window.Clerk.session.getToken();

        if (!token) {
            throw new Error("Unable to obtain your sign-in session.");
        }

        return token;
    }

    async function sendApiRequest(url, options = {}) {
        const token = await getSessionToken();

        const response = await fetch(url, {
            ...options,
            headers: {
                ...(options.headers || {}),
                Authorization: `Bearer ${token}`,
            },
            credentials: "same-origin",
        });

        const result = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(
                result.error || `Request failed (${response.status}).`
            );
        }

        return result;
    }

    async function checkExistingProfile() {
        const result = await sendApiRequest("/api/me");

        if (!result.authenticated) {
            throw new Error("The server could not verify your account.");
        }

        profileSection.hidden = false;
        profileMessage.textContent =
            "Choose your university to complete your profile.";

        return result;
    }

    function setProfileMessage(message, type = "") {
        profileMessage.textContent = message;
        profileMessage.className = "profile-message";

        if (type) {
            profileMessage.classList.add(`profile-message-${type}`);
        }
    }

    async function handleProfileSubmit(event) {
        event.preventDefault();

        const selectedUniversity = universitySelect.value;
        const university = selectedUniversity === "Other"
            ? otherUniversityInput.value.trim()
            : selectedUniversity;

        if (!university) {
            setProfileMessage("Please select or enter your university.", "error");
            return;
        }

        if (university.length > 150) {
            setProfileMessage(
                "University names must be 150 characters or fewer.",
                "error"
            );
            return;
        }

        saveProfileButton.disabled = true;
        saveProfileButton.textContent = "Saving...";
        setProfileMessage("Saving your profile...");

        try {
            const result = await sendApiRequest("/api/profile", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ university }),
            });

            const profile = result.profile;

            universitySelect.value = profile.university;
            otherUniversityInput.value = "";
            otherUniversityContainer.hidden = true;

            setProfileMessage(
                `Profile saved! Student verification status: ${profile.verification_status}.`,
                "success"
            );
        } catch (error) {
            console.error("Profile save failed:", error);
            setProfileMessage(error.message || "Unable to save your profile.", "error");
        } finally {
            saveProfileButton.disabled = false;
            saveProfileButton.textContent = "Save profile";
        }
    }

    async function initialiseClerk() {
        try {
            if (!window.Clerk) {
                throw new Error(
                    "Clerk did not load. Check the browser console and network connection."
                );
            }

            await window.Clerk.load({
                ui: {
                    ClerkUI: window.__internal_ClerkUICtor,
                },
            });

            signInButton.addEventListener("click", () => {
                window.Clerk.openSignIn();
            });

            signUpButton.addEventListener("click", () => {
                window.Clerk.openSignUp();
            });

            universitySelect?.addEventListener("change", () => {
                const isOther = universitySelect.value === "Other";

                otherUniversityContainer.hidden = !isOther;
                otherUniversityInput.required = isOther;

                if (!isOther) {
                    otherUniversityInput.value = "";
                }
            });

            profileForm?.addEventListener("submit", handleProfileSubmit);

            if (window.Clerk.isSignedIn && window.Clerk.user) {
                showSignedIn(window.Clerk.user);
                window.Clerk.mountUserButton(userButtonContainer);

                try {
                    await checkExistingProfile();
                } catch (error) {
                    statusElement.textContent =
                        "Signed in; profile setup needs attention";
                    console.error("Profile initialisation failed:", error);

                    if (profileSection) {
                        profileSection.hidden = false;
                    }

                    setProfileMessage(
                        "We couldn't verify your profile. Please refresh and try again.",
                        "error"
                    );
                }

                return;
            }

            showSignedOut();
        } catch (error) {
            statusElement.textContent = "Account service unavailable";
            console.error("Clerk initialisation failed:", error);
        }
    }

    window.addEventListener("load", initialiseClerk);
})();
