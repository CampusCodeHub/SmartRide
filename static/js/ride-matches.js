(() => {
    "use strict";

    const dashboard = document.getElementById("matching-dashboard");

    if (!dashboard) {
        return;
    }

    const button = document.getElementById("find-matches-button");
    const status = document.getElementById("matching-status");
    const matchList = document.getElementById("match-list");
    const matchesUrl = dashboard.dataset.matchesUrl;

    let loading = false;
    let passengerMarkerLayer = null;

    function showStatus(message, type = "") {
        status.textContent = message;
        status.className = `matching-status ${type}`.trim();
    }

    async function getSessionToken() {
        if (!window.Clerk) {
            throw new Error(
                "Clerk authentication is unavailable. Please refresh."
            );
        }

        await window.Clerk.load();

        if (!window.Clerk.session) {
            throw new Error(
                "Please sign in before viewing potential matches."
            );
        }

        const token = await window.Clerk.session.getToken();

        if (!token) {
            throw new Error(
                "Your session could not be verified. Please sign in again."
            );
        }

        return token;
    }

    function createDetail(label, value) {
        const container = document.createElement("div");
        container.className = "match-detail";

        const heading = document.createElement("span");
        heading.textContent = label;

        const detail = document.createElement("strong");
        detail.textContent = value;

        container.append(heading, detail);

        return container;
    }

    function formatDistance(value) {
        if (value === null || value === undefined || value === "") {
            return "Not available";
        }

        const distance = Number(value);

        return Number.isFinite(distance)
            ? `${distance.toFixed(2)} km`
            : "Not available";
    }

    function formatMinutes(value) {
        if (value === null || value === undefined || value === "") {
            return "Not available";
        }

        const minutes = Number(value);

        return Number.isFinite(minutes)
            ? `${minutes.toFixed(1)} min`
            : "Not available";
    }

    function validCoordinates(latitude, longitude) {
        const lat = Number(latitude);
        const lng = Number(longitude);

        return (
            Number.isFinite(lat) &&
            Number.isFinite(lng) &&
            lat >= -90 &&
            lat <= 90 &&
            lng >= -180 &&
            lng <= 180
        );
    }

    function createLocationIcon(type) {
        const colour = type === "pickup" ? "#79ad39" : "#2878c8";
        const letter = type === "pickup" ? "P" : "D";

        return L.divIcon({
            className: "smartride-location-marker",
            html: `
                <div style="
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50% 50% 50% 0;
                    transform: rotate(-45deg);
                    background: ${colour};
                    border: 2px solid white;
                    box-shadow: 0 2px 7px rgba(0,0,0,0.3);
                    color: white;
                    font-weight: 800;
                    font-size: 12px;
                ">
                    <span style="transform: rotate(45deg);">${letter}</span>
                </div>
            `,
            iconSize: [30, 30],
            iconAnchor: [15, 30],
            popupAnchor: [0, -30]
        });
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[character]);
    }

    function addPassengerMarkers(matches) {
        if (typeof L === "undefined") {
            console.warn("Leaflet is unavailable. Passenger markers skipped.");
            return 0;
        }

        const mapElement = document.getElementById("journey-map");

        if (!mapElement) {
            return 0;
        }

        const map = window.smartRideMap;

        if (!map) {
            console.warn(
                "SmartRide map instance unavailable. Passenger markers skipped."
            );
            return 0;
        }

        if (passengerMarkerLayer) {
            map.removeLayer(passengerMarkerLayer);
        }

        passengerMarkerLayer = L.layerGroup().addTo(map);

        let markerCount = 0;

        matches.forEach((match, index) => {
            const passengerNumber = index + 1;

            const pickupValid = validCoordinates(
                match.pickup_latitude,
                match.pickup_longitude
            );

            const dropoffValid = validCoordinates(
                match.dropoff_latitude,
                match.dropoff_longitude
            );

            if (pickupValid) {
                const pickup = [
                    Number(match.pickup_latitude),
                    Number(match.pickup_longitude)
                ];

                L.marker(pickup, {
                    icon: createLocationIcon("pickup")
                })
                    .bindPopup(`
                        <strong>Passenger ${passengerNumber} — Pickup</strong>
                        <br>
                        ${escapeHtml(match.pickup_address || "Pickup location")}
                    `)
                    .addTo(passengerMarkerLayer);

                markerCount++;
            }

            if (dropoffValid) {
                const dropoff = [
                    Number(match.dropoff_latitude),
                    Number(match.dropoff_longitude)
                ];

                L.marker(dropoff, {
                    icon: createLocationIcon("dropoff")
                })
                    .bindPopup(`
                        <strong>Passenger ${passengerNumber} — Drop-off</strong>
                        <br>
                        ${escapeHtml(match.dropoff_address || "Drop-off location")}
                    `)
                    .addTo(passengerMarkerLayer);

                markerCount++;
            }
        });

        console.log(
            `SmartRide: ${markerCount} passenger location markers added.`
        );

        return markerCount;
    }

    function getVerificationStatus(match) {
        switch (match.road_route_status) {
            case "accepted":
                return {
                    label: "Road verified",
                    className: "verified"
                };

            case "rejected":
                return {
                    label: "Detour exceeded",
                    className: "rejected"
                };

            case "unavailable":
                return {
                    label: "Verification pending",
                    className: "pending"
                };

            default:
                return {
                    label: "Potential match",
                    className: "potential"
                };
        }
    }

    function renderMatch(match, index) {
        const card = document.createElement("article");
        card.className = "match-card";

        const top = document.createElement("div");
        top.className = "match-card-top";

        const heading = document.createElement("h3");
        heading.textContent = `Potential passenger ${index + 1}`;

        const badge = document.createElement("span");
        const verification = getVerificationStatus(match);

        badge.className = `match-status ${verification.className}`;
        badge.textContent = verification.label;

        top.append(heading, badge);

        const details = document.createElement("div");
        details.className = "match-details";

        details.append(
            createDetail(
                "Passengers",
                String(match.passenger_count ?? "Not available")
            ),
            createDetail(
                "Pickup distance",
                formatDistance(match.pickup_distance_km)
            ),
            createDetail(
                "Drop-off distance",
                formatDistance(match.dropoff_distance_km)
            ),
            createDetail(
                "Departure difference",
                formatMinutes(match.departure_difference_minutes)
            )
        );

        // Display road-route calculations when verification succeeded.
        if (match.road_route_verified === true) {
            details.append(
                createDetail(
                    "Original journey",
                    formatMinutes(match.original_route_duration_minutes)
                ),
                createDetail(
                    "Shared journey",
                    formatMinutes(match.shared_route_duration_minutes)
                ),
                createDetail(
                    "Additional travel time",
                    formatMinutes(match.additional_travel_time_minutes)
                ),
                createDetail(
                    "Maximum extra time",
                    formatMinutes(match.maximum_detour_minutes)
                )
            );
        }

        const explanation = document.createElement("p");
        explanation.className = "match-explanation";
        explanation.textContent =
            match.explanation ||
            "This request passed the initial journey screening.";

        card.append(top, details, explanation);

        return card;
    }

    function updateMatchingSummary(data) {
        const accepted = data.verified_match_count ?? 0;
        const rejected = data.rejected_match_count ?? 0;
        const pending = data.pending_verification_count ?? 0;

        const summary = [];

        if (accepted > 0) {
            summary.push(`${accepted} road-verified`);
        }

        if (rejected > 0) {
            summary.push(`${rejected} rejected`);
        }

        if (pending > 0) {
            summary.push(`${pending} pending verification`);
        }

        return summary.length > 0
            ? summary.join(" · ")
            : "No road-verified matches yet.";
    }

    // ---------------------------------------------------------
    // Optimised passenger group
    // ---------------------------------------------------------

    function renderOptimisedGroup(data) {
        const panel = document.getElementById("optimised-group-panel");
        const description = document.getElementById("group-description");
        const details = document.getElementById("group-details");
        const passengerList = document.getElementById("group-passenger-list");
        const message = document.getElementById("group-message");

        if (!panel || !description || !details || !passengerList || !message) {
            return;
        }

        // Reset the previous result before rendering a new one.
        panel.hidden = true;
        details.replaceChildren();
        passengerList.replaceChildren();
        message.textContent = "";

        const group = data.selected_group;

        // Handle cases where no feasible group was selected.
        if (!group || group.status !== "selected_group") {
            const statusMessages = {
                no_verified_candidates:
                    "No passengers passed road-route verification, so a group could not be selected.",

                no_feasible_group:
                    "No combination of passengers currently fits the available seats and detour limits.",

                unavailable:
                    "Group optimisation is temporarily unavailable. Individual matching results are still shown.",

                not_run:
                    "Group optimisation has not been run for this search.",

                offer_not_found:
                    "The ride offer could not be found."
            };

            const explanation =
                data.group_optimisation_message ||
                statusMessages[data.group_optimisation_status] ||
                "No suitable passenger group was selected for this journey.";

            description.textContent = "No recommended group is available yet.";
            message.textContent = explanation;
            panel.hidden = false;

            return;
        }

        const requestIds = Array.isArray(group.request_ids)
            ? group.request_ids
            : [];

        // Match selected request IDs to the individual match objects.
        const selectedMatches = requestIds
            .map(requestId => data.matches.find(
                match => String(match.request_id) === String(requestId)
            ))
            .filter(Boolean);

        if (selectedMatches.length === 0) {
            description.textContent = "Group selection needs to be refreshed.";

            message.textContent =
                "The server returned a selected group, but its passenger requests could not be matched to the displayed results.";

            panel.hidden = false;

            return;
        }

        description.textContent =
            "The optimisation engine selected this feasible combination using passenger capacity, route duration and detour constraints.";

        // Group optimisation metrics.
        const groupDetails = [
            [
                "Ride requests",
                String(group.group_size ?? requestIds.length)
            ],
            [
                "Total passengers",
                String(group.passenger_count ?? "Not available")
            ],
            [
                "Original journey",
                formatMinutes(group.original_duration_minutes)
            ],
            [
                "Shared journey",
                formatMinutes(group.shared_duration_minutes)
            ],
            [
                "Additional travel time",
                formatMinutes(group.additional_travel_time_minutes)
            ],
            [
                "Maximum detour",
                formatMinutes(group.maximum_detour_minutes)
            ]
        ];

        groupDetails.forEach(([label, value]) => {
            details.appendChild(createDetail(label, value));
        });

        // Display the selected passenger requests.
        selectedMatches.forEach((match, index) => {
            const passenger = document.createElement("div");
            passenger.className = "group-passenger";

            const heading = document.createElement("strong");
            heading.textContent = `Passenger request ${index + 1}`;

            const information = document.createElement("p");

            information.textContent =
                `${match.passenger_count ?? "?"} passenger(s) · ` +
                `${match.pickup_address || "Pickup unavailable"} → ` +
                `${match.dropoff_address || "Drop-off unavailable"}`;

            passenger.append(heading, information);
            passengerList.appendChild(passenger);
        });

        message.textContent =
            "This is a recommendation only. No passenger bookings have been confirmed.";

        panel.hidden = false;
    }

    // ---------------------------------------------------------
    // Retrieve and display matching results
    // ---------------------------------------------------------

    async function loadMatches() {
        if (loading) {
            return;
        }

        loading = true;
        button.disabled = true;
        button.textContent = "Searching for passengers...";
        matchList.replaceChildren();

        const groupPanel = document.getElementById("optimised-group-panel");

        if (groupPanel) {
            groupPanel.hidden = true;
        }

        showStatus(
            "Checking compatible requests and verifying road detours..."
        );

        try {
            const token = await getSessionToken();

            const response = await fetch(matchesUrl, {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${token}`,
                    Accept: "application/json"
                },
                credentials: "same-origin"
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(
                    data.error || "Unable to retrieve potential matches."
                );
            }

            if (!Array.isArray(data.matches)) {
                throw new Error(
                    "The server returned an unexpected matching response."
                );
            }

            // No individual matches.
            if (data.matches.length === 0) {
                addPassengerMarkers([]);
                renderOptimisedGroup(data);

                showStatus(
                    "No potential passengers were found for this offer yet.",
                    "success"
                );

                return;
            }

            // Render individual passenger match cards.
            const fragment = document.createDocumentFragment();

            data.matches.forEach((match, index) => {
                fragment.appendChild(renderMatch(match, index));
            });

            matchList.appendChild(fragment);

            // Render the selected group returned by the backend.
            renderOptimisedGroup(data);

            // Add passenger pickup and drop-off markers to the map.
            const markerCount = addPassengerMarkers(data.matches);

            const summary = updateMatchingSummary(data);

            showStatus(
                `${data.match_count ?? data.matches.length} passenger request(s) found. ` +
                `${markerCount} location marker(s) displayed. ${summary}`,
                "success"
            );

        } catch (error) {
            console.error("Matching request failed:", error);

            showStatus(
                error.message ||
                "Something went wrong while finding matches.",
                "error"
            );

        } finally {
            loading = false;
            button.disabled = false;
            button.textContent = "Refresh Potential Matches →";
        }
    }

    button.addEventListener("click", loadMatches);

})();