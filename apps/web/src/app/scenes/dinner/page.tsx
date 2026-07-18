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
        <h1 style={{ fontSize: "var(--font-size-xl)" }}>宿舍聚餐</h1>
        <Link href="/scenes/dinner/result" className="btn">
          查看结果 →
        </Link>
      </div>

      {loading && <LoadingState message="正在加载场景..." />}
      {error && <ErrorState message="加载场景失败。" />}
      {scene && (
        <>
          <div className="card">
            <div style={{ display: "flex", gap: "var(--space-md)", alignItems: "center" }}>
              <StatusBadge label={scene.status} variant="info" />
              <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                {scene.participant_count} 名参与者
              </span>
            </div>
          </div>

          {scene.has_submitted ? (
            <div className="card" style={{ borderColor: "var(--color-success)", background: "var(--color-success-light)" }}>
              <p style={{ color: "var(--color-success)", fontWeight: "var(--font-weight-medium)" }}>
                ✓ 你的偏好已提交。
              </p>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-xs)" }}>
                可前往 <Link href="/scenes/dinner/result">结果页</Link> 查看聚合推荐。
              </p>
            </div>
          ) : submitStatus === "success" ? (
            <div className="card" style={{ borderColor: "var(--color-success)", background: "var(--color-success-light)" }}>
              <p style={{ color: "var(--color-success)", fontWeight: "var(--font-weight-medium)" }}>
                ✓ 偏好已提交成功。
              </p>
            </div>
          ) : (
            <div className="card">
              {/* Privacy notice MUST appear before input fields */}
              <PrivacyNotice title="私密偏好提交">
                <p style={{ marginBottom: "var(--space-xs)" }}>
                  &#8226; <strong>可见性：</strong> 只有你可以看到原始偏好，其他成员只能看到聚合结果。
                </p>
                <p style={{ marginBottom: "var(--space-xs)" }}>
                  &#8226; <strong>使用目的：</strong> 仅用于餐厅推荐匹配。
                </p>
                <p style={{ marginBottom: "var(--space-xs)" }}>
                  &#8226; <strong>保留期限：</strong> 场景结束后删除，最长不超过 24 小时。
                </p>
                <p>
                  &#8226; <strong>删除：</strong> 你可以在场景结束前随时删除自己的提交。
                </p>
              </PrivacyNotice>

              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
                <div>
                  <label htmlFor="budget" style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                    预算范围（元）
                  </label>
                  <input
                    id="budget"
                    className="input"
                    placeholder="例如：20-50"
                    value={budget}
                    onChange={(e) => setBudget(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                    饮食限制
                  </label>
                  <div style={{ display: "flex", gap: "var(--space-sm)", flexWrap: "wrap" }}>
                    {["素食", "清真", "不吃辣", "无麸质", "无"].map((d) => (
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
                    偏好时间
                  </label>
                  <select
                    id="time"
                    className="input"
                    value={timeSlot}
                    onChange={(e) => setTimeSlot(e.target.value)}
                  >
                    <option value="">请选择时间...</option>
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
                  {submitting ? "提交中..." : "提交偏好"}
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
