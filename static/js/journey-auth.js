
(() => {
    "use strict";

    const form = document.querySelector(".journey-form-card");

    if (!form) {
        return;
    }

    let submitting = false;

    function showError(message) {
        let errorBox = form.querySelector(".journey-error");

        if (!errorBox) {
            errorBox = document.createElement("div");
            errorBox.className = "journey-error";
            errorBox.setAttribute("role", "alert");
            form.prepend(errorBox);
        }

        errorBox.textContent = message;
    }

    async function getSessionToken() {
        if (!window.Clerk) {
            throw new Error("Clerk authentication is unavailable. Please refresh.");
        }

        await window.Clerk.load();

        if (!window.Clerk.session) {
            throw new Error("Please sign in before submitting your journey.");
        }

        const token = await window.Clerk.session.getToken();

        if (!token) {
            throw new Error("Your session could not be verified. Please sign in again.");
        }

        return token;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (submitting) {
            return;
        }

        submitting = true;

        const submitButton = form.querySelector(
            'button[type="submit"]'
        );

        const originalButtonContent = submitButton.innerHTML;

        submitButton.disabled = true;
        submitButton.textContent = "Submitting...";

        try {
            const token = await getSessionToken();

            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                credentials: "same-origin",
                body: new FormData(form),
            });

            const html = await response.text();

            if (!html) {
                throw new Error("The server returned an empty response.");
            }

            history.replaceState(null, "", response.url);

            document.open();
            document.write(html);
            document.close();

        } catch (error) {
            console.error("Journey submission failed:", error);

            showError(
                error.message || "Unable to submit your journey. Please try again."
            );

            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonContent;
            submitting = false;
        }
    });
})();
