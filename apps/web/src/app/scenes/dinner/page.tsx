"use client";

import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PrivacyNotice } from "@/components/privacy/PrivacyNotice";
import { apiGet, apiPost } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import { useState } from "react";
import Link from "next/link";

interface DinnerScene {
  id: string;
  status: string;
  participant_count: number;
  has_submitted: boolean;
}

function DinnerContent() {
  const [submitting, setSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<"idle" | "success">("idle");
  const [budget, setBudget] = useState("");
  const [dietary, setDietary] = useState<string[]>([]);
  const [timeSlot, setTimeSlot] = useState("");

  const { data: scene, loading, error, reload } = useAsync<DinnerScene>(
    async () => apiGet("/scenes/dorm_dinner/status"),
    [],
  );

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await apiPost("/scenes/dorm_dinner/preferences", {
        budget_range: budget,
        dietary_restrictions: dietary,
        preferred_time: timeSlot,
      });
      setSubmitStatus("success");
      reload();
    } catch {
      // Error is handled by error state
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ fontSize: "var(--font-size-xl)" }}>Dorm Dinner</h1>
        <Link href="/scenes/dinner/result" className="btn">
          View Results →
        </Link>
      </div>

      {loading && <LoadingState message="Loading scene..." />}
      {error && <ErrorState message="Failed to load scene." />}
      {scene && (
        <>
          <div className="card">
            <div style={{ display: "flex", gap: "var(--space-md)", alignItems: "center" }}>
              <StatusBadge label={scene.status} variant="info" />
              <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                {scene.participant_count} participant{scene.participant_count !== 1 ? "s" : ""}
              </span>
            </div>
          </div>

          {scene.has_submitted ? (
            <div className="card" style={{ borderColor: "var(--color-success)", background: "var(--color-success-light)" }}>
              <p style={{ color: "var(--color-success)", fontWeight: "var(--font-weight-medium)" }}>
                ✓ Your preferences have been submitted.
              </p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-xs)" }}>
                Check the <Link href="/scenes/dinner/result">results page</Link> for aggregated recommendations.
              </p>
            </div>
          ) : submitStatus === "success" ? (
            <div className="card" style={{ borderColor: "var(--color-success)", background: "var(--color-success-light)" }}>
              <p style={{ color: "var(--color-success)", fontWeight: "var(--font-weight-medium)" }}>
                ✓ Preferences submitted successfully.
              </p>
            </div>
          ) : (
            <div className="card">
              {/* Privacy notice MUST appear before input fields */}
              <PrivacyNotice title="Private Preference Submission">
                <p style={{ marginBottom: "var(--space-xs)" }}>
                  &#8226; <strong>Visibility:</strong> Only you can see your raw preferences. Other members only see aggregated results.
                </p>
                <p style={{ marginBottom: "var(--space-xs)" }}>
                  &#8226; <strong>Purpose:</strong> Used only for restaurant recommendation matching.
                </p>
                <p style={{ marginBottom: "var(--space-xs)" }}>
                  &#8226; <strong>Retention:</strong> Deleted after the scene ends, or within 24 hours at most.
                </p>
                <p>
                  &#8226; <strong>Deletion:</strong> You can delete your submission at any time before the scene ends.
                </p>
              </PrivacyNotice>

              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
                <div>
                  <label htmlFor="budget" style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                    Budget Range (CNY)
                  </label>
                  <input
                    id="budget"
                    className="input"
                    placeholder="e.g. 20-50"
                    value={budget}
                    onChange={(e) => setBudget(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                    Dietary Restrictions
                  </label>
                  <div style={{ display: "flex", gap: "var(--space-sm)", flexWrap: "wrap" }}>
                    {["Vegetarian", "Halal", "No Spice", "Gluten Free", "None"].map((d) => (
                      <label key={d} style={{ display: "flex", alignItems: "center", gap: "var(--space-xs)", fontSize: "var(--font-size-sm)" }}>
                        <input
                          type="checkbox"
                          checked={dietary.includes(d)}
                          onChange={(e) => {
                            if (e.target.checked) setDietary([...dietary, d]);
                            else setDietary(dietary.filter((x) => x !== d));
                          }}
                        />
                        {d}
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label htmlFor="time" style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                    Preferred Time
                  </label>
                  <select
                    id="time"
                    className="input"
                    value={timeSlot}
                    onChange={(e) => setTimeSlot(e.target.value)}
                  >
                    <option value="">Select a time...</option>
                    <option value="17:00">17:00 - 18:00</option>
                    <option value="18:00">18:00 - 19:00</option>
                    <option value="19:00">19:00 - 20:00</option>
                    <option value="20:00">20:00 - 21:00</option>
                  </select>
                </div>

                <button
                  className="btn btn-primary"
                  onClick={handleSubmit}
                  disabled={submitting || (!budget && dietary.length === 0 && !timeSlot)}
                >
                  {submitting ? "Submitting..." : "Submit Preferences"}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function DinnerPage() {
  return (
    <AppShell requireAuth>
      <DinnerContent />
    </AppShell>
  );
}
