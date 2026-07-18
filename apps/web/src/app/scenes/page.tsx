"use client";

import { AppShell } from "@/components/app/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import Link from "next/link";

interface SceneInfo {
  key: string;
  title: string;
  description: string;
  status: "available" | "concept";
  privacySummary: string;
  dataTypes: string[];
}

const SCENES: SceneInfo[] = [
  {
    key: "dorm_dinner",
    title: "Dorm Dinner",
    description: "Negotiate dinner plans with your dorm mates. Submit private preferences and get aggregated restaurant recommendations.",
    status: "available",
    privacySummary: "Private preferences are encrypted and only used for aggregation. Other members only see aggregated results.",
    dataTypes: ["Dietary restrictions", "Budget range", "Time preferences", "Location constraints"],
  },
  {
    key: "study_group",
    title: "Study Group",
    description: "Find study partners based on courses and schedules.",
    status: "concept",
    privacySummary: "Course schedules will be used only for matching.",
    dataTypes: ["Course schedule", "Study preferences"],
  },
  {
    key: "room_share",
    title: "Room Share",
    description: "Split dorm expenses with roommates.",
    status: "concept",
    privacySummary: "Expense data will be used only for calculation.",
    dataTypes: ["Expense items", "Payment preferences"],
  },
];

function ScenesContent() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>Scenes</h1>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "var(--space-md)" }}>
        {SCENES.map((scene) => (
          <div key={scene.key} className="card" style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>{scene.title}</h3>
              <StatusBadge
                label={scene.status === "available" ? "Available" : "Coming Soon"}
                variant={scene.status === "available" ? "success" : "default"}
              />
            </div>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
              {scene.description}
            </p>

            <div style={{ background: "var(--color-privacy-light)", padding: "var(--space-sm)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-privacy)", fontWeight: "var(--font-weight-medium)", marginBottom: "var(--space-xs)" }}>
                🔒 Privacy
              </p>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-primary)" }}>
                {scene.privacySummary}
              </p>
            </div>

            <div>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginBottom: "var(--space-xs)" }}>
                Data used:
              </p>
              <div style={{ display: "flex", gap: "var(--space-xs)", flexWrap: "wrap" }}>
                {scene.dataTypes.map((dt) => (
                  <span key={dt} className="badge">{dt}</span>
                ))}
              </div>
            </div>

            {scene.status === "available" ? (
              <Link href={`/scenes/${scene.key}`} className="btn btn-primary" style={{ marginTop: "var(--space-sm)", textAlign: "center" }}>
                Enter Scene
              </Link>
            ) : (
              <button className="btn" disabled style={{ marginTop: "var(--space-sm)" }}>
                Coming Soon
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ScenesPage() {
  return (
    <AppShell requireAuth>
      <ScenesContent />
    </AppShell>
  );
}
