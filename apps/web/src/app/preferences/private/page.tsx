"use client";

import { AppShell } from "@/components/app/AppShell";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PrivacyNotice } from "@/components/privacy/PrivacyNotice";
import { DangerConfirm } from "@/components/privacy/DangerConfirm";
import { apiGet, apiPost, apiDelete } from "@/lib/api/client";
import { useAsync } from "@/lib/useAsync";
import { useState } from "react";

interface PrivatePreference {
  id: string;
  scene_key: string;
  submitted_at: string;
  status: string;
}

function PrivatePreferencesContent() {
  const [budget, setBudget] = useState("");
  const [dietary, setDietary] = useState<string[]>([]);
  const [timeSlot, setTimeSlot] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const { data: prefs, loading, error, reload } = useAsync<PrivatePreference[]>(
    async () => apiGet("/scenes/dorm_dinner/preferences"),
    [reloadKey],
  );

  const handleSubmit = async () => {
    setSubmitting(true);
    setSuccess(false);
    try {
      await apiPost("/scenes/dorm_dinner/preferences", {
        budget_range: budget,
        dietary_restrictions: dietary,
        preferred_time: timeSlot,
      });
      setSuccess(true);
      setBudget("");
      setDietary([]);
      setTimeSlot("");
      reload();
    } catch {
      // Error handled by state
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (prefId: string) => {
    await apiDelete(`/scenes/dorm_dinner/preferences/${prefId}`);
    setReloadKey((k) => k + 1);
    reload();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>Private Preferences</h1>

      {/* Privacy notice MUST appear before input fields */}
      <PrivacyNotice title="Private Preference Management">
        <p style={{ marginBottom: "var(--space-xs)" }}>
          &#8226; <strong>Visibility:</strong> Only you can see your raw preferences. Other members only see aggregated results.
        </p>
        <p style={{ marginBottom: "var(--space-xs)" }}>
          &#8226; <strong>Purpose:</strong> Used only for scene recommendation algorithms.
        </p>
        <p style={{ marginBottom: "var(--space-xs)" }}>
          &#8226; <strong>Retention:</strong> Deleted after the scene ends, or within 24 hours at most.
        </p>
        <p>
          &#8226; <strong>Deletion:</strong> You can delete your submission at any time. Preferences are never stored in browser storage.
        </p>
      </PrivacyNotice>

      {/* Existing preferences (metadata only, no content) */}
      <div className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>Submitted Preferences</h2>
        {loading && <LoadingState message="Loading..." />}
        {error && <ErrorState message="Failed to load preferences." />}
        {prefs && prefs.length === 0 && (
          <EmptyState title="No preferences submitted" description="Submit your preferences using the form below." />
        )}
        {prefs && prefs.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            {prefs.map((p) => (
              <div key={p.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-sm)", borderRadius: "var(--radius-md)", background: "var(--color-surface-hover)" }}>
                <div>
                  <StatusBadge label={p.scene_key} variant="info" />
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginLeft: "var(--space-sm)" }}>
                    Submitted: {new Date(p.submitted_at).toLocaleString()}
                  </span>
                </div>
                <DangerConfirm
                  trigger={<button className="btn btn-sm btn-danger">Delete</button>}
                  title="Delete Preference"
                  message="Are you sure you want to delete this preference? This action cannot be undone."
                  confirmLabel="Delete"
                  onConfirm={() => handleDelete(p.id)}
                />
              </div>
            ))}
          </div>
        )}
        <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-sm)" }}>
          Preference content is not displayed for privacy. Only submission metadata is shown.
        </p>
      </div>

      {/* Submit new preference */}
      {success ? (
        <div className="card" style={{ borderColor: "var(--color-success)", background: "var(--color-success-light)" }}>
          <p style={{ color: "var(--color-success)", fontWeight: "var(--font-weight-medium)" }}>
            ✓ Preferences submitted successfully. Content is not displayed for privacy.
          </p>
          <button className="btn" onClick={() => setSuccess(false)} style={{ marginTop: "var(--space-sm)" }}>
            Submit another
          </button>
        </div>
      ) : (
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>Submit New Preference</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
            <div>
              <label htmlFor="pref-budget" style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                Budget Range (CNY)
              </label>
              <input id="pref-budget" className="input" placeholder="e.g. 20-50" value={budget} onChange={(e) => setBudget(e.target.value)} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                Dietary Restrictions
              </label>
              <div style={{ display: "flex", gap: "var(--space-sm)", flexWrap: "wrap" }}>
                {["Vegetarian", "Halal", "No Spice", "Gluten Free", "None"].map((d) => (
                  <label key={d} style={{ display: "flex", alignItems: "center", gap: "var(--space-xs)", fontSize: "var(--font-size-sm)" }}>
                    <input type="checkbox" checked={dietary.includes(d)} onChange={(e) => { if (e.target.checked) setDietary([...dietary, d]); else setDietary(dietary.filter((x) => x !== d)); }} />
                    {d}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label htmlFor="pref-time" style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                Preferred Time
              </label>
              <select id="pref-time" className="input" value={timeSlot} onChange={(e) => setTimeSlot(e.target.value)}>
                <option value="">Select a time...</option>
                <option value="17:00">17:00 - 18:00</option>
                <option value="18:00">18:00 - 19:00</option>
                <option value="19:00">19:00 - 20:00</option>
                <option value="20:00">20:00 - 21:00</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting || (!budget && dietary.length === 0 && !timeSlot)}>
              {submitting ? "Submitting..." : "Submit Preferences"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function PrivatePreferencesPage() {
  return (
    <AppShell requireAuth>
      <PrivatePreferencesContent />
    </AppShell>
  );
}
