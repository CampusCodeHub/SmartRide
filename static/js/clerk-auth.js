
(() => {
    "use strict";

    const statusElement = document.getElementById("auth-status");
    const signInButton = document.getElementById("sign-in-button");
    const signUpButton = document.getElementById("sign-up-button");
    const userButtonContainer = document.getElementById("user-button");

    const profileSection = document.getElementById("profile-setup");
    const profileFormContainer = document.getElementById(
        "profile-form-container"
    );
    const savedProfileContainer = document.getElementById(
        "saved-profile-container"
    );

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
            const error = new Error(
                result.error || `Request failed (${response.status}).`
            );

            error.status = response.status;
            throw error;
        }

        return result;
    }

    function setProfileMessage(message, type = "") {
        if (!profileMessage) {
            return;
        }

        profileMessage.textContent = message;
        profileMessage.className = "profile-message";

        if (type) {
            profileMessage.classList.add(`profile-message-${type}`);
        }
    }

    function showProfileSetup() {
        profileSection.hidden = false;
        profileFormContainer.hidden = false;
        savedProfileContainer.hidden = true;

        setProfileMessage(
            "Choose your university to complete your profile."
        );
    }

    function showSavedProfile(profile) {
        profileSection.hidden = false;
        profileFormContainer.hidden = true;
        savedProfileContainer.hidden = false;

        document.getElementById("saved-profile-name").textContent =
            profile.display_name || "Student";

        document.getElementById("saved-profile-university").textContent =
            profile.university || "Not provided";

        document.getElementById("saved-profile-email").textContent =
            profile.email || "Not provided";

        document.getElementById("saved-profile-account-status").textContent =
            formatStatus(profile.account_status);

        const verificationStatus = formatStatus(
            profile.verification_status
        );

        document.getElementById("saved-profile-verification").textContent =
            verificationStatus;

        const badge = document.getElementById(
            "verification-status-badge"
        );

        badge.textContent = verificationStatus;
        badge.className = `verification-badge verification-${String(
            profile.verification_status || "pending"
        ).toLowerCase()}`;

        const message = document.getElementById(
            "saved-profile-message"
        );

        if (profile.verification_status === "pending") {
            message.textContent =
                "Your student verification is pending. We'll update this when your eligibility has been checked.";
        } else if (profile.verification_status === "verified") {
            message.textContent =
                "Your student profile has been verified.";
        } else {
            message.textContent =
                "Your current student verification status is shown above.";
        }
    }

    function formatStatus(value) {
        if (!value) {
            return "Unknown";
        }

        return String(value)
            .replaceAll("_", " ")
            .replace(/\b\w/g, character => character.toUpperCase());
    }

    async function checkExistingProfile() {
        profileSection.hidden = false;

        try {
            const result = await sendApiRequest("/api/profile");

            showSavedProfile(result.profile);
        } catch (error) {
            if (error.status === 404) {
                showProfileSetup();
                return;
            }

            throw error;
        }
    }

    async function handleProfileSubmit(event) {
        event.preventDefault();

        const selectedUniversity = universitySelect.value;

        const university = selectedUniversity === "Other"
            ? otherUniversityInput.value.trim()
            : selectedUniversity;

        if (!university) {
            setProfileMessage(
                "Please select or enter your university.",
                "error"
            );
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

            showSavedProfile(result.profile);

        } catch (error) {
            console.error("Profile save failed:", error);

            setProfileMessage(
                error.message || "Unable to save your profile.",
                "error"
            );

        } finally {
            saveProfileButton.disabled = false;
            saveProfileButton.innerHTML =
                'Save my profile <span aria-hidden="true">↗</span>';
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

            profileForm?.addEventListener(
                "submit",
                handleProfileSubmit
            );

            if (window.Clerk.isSignedIn && window.Clerk.user) {
                showSignedIn(window.Clerk.user);

                window.Clerk.mountUserButton(userButtonContainer);

                try {
                    await checkExistingProfile();
                } catch (error) {
                    statusElement.textContent =
                        "Signed in; profile needs attention";

                    console.error(
                        "Profile initialisation failed:",
                        error
                    );

                    profileSection.hidden = false;
                    profileFormContainer.hidden = true;
                    savedProfileContainer.hidden = true;

                    setProfileMessage(
                        "We couldn't retrieve your profile. Please refresh and try again.",
                        "error"
                    );
                }

                return;
            }

            showSignedOut();

        } catch (error) {
            statusElement.textContent = "Account service unavailable";

            console.error(
                "Clerk initialisation failed:",
                error
            );
        }
    }

    window.addEventListener("load", initialiseClerk);
})();
