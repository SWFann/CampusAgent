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
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>私密偏好</h1>

      {/* Privacy notice MUST appear before input fields */}
      <PrivacyNotice title="私密偏好管理">
        <p style={{ marginBottom: "var(--space-xs)" }}>
          &#8226; <strong>可见性：</strong> 只有你可以看到原始偏好，其他成员只能看到聚合结果。
        </p>
        <p style={{ marginBottom: "var(--space-xs)" }}>
          &#8226; <strong>使用目的：</strong> 仅用于场景推荐算法。
        </p>
        <p style={{ marginBottom: "var(--space-xs)" }}>
          &#8226; <strong>保留期限：</strong> 场景结束后删除，最长不超过 24 小时。
        </p>
        <p>
          &#8226; <strong>删除：</strong> 你可以随时删除自己的提交。偏好不会存入浏览器存储。
        </p>
      </PrivacyNotice>

      {/* Existing preferences (metadata only, no content) */}
      <div className="card">
        <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>已提交的偏好</h2>
        {loading && <LoadingState message="加载中..." />}
        {error && <ErrorState message="加载偏好失败。" />}
        {prefs && prefs.length === 0 && (
          <EmptyState title="暂无已提交偏好" description="可使用下方表单提交偏好。" />
        )}
        {prefs && prefs.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            {prefs.map((p) => (
              <div key={p.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-sm)", borderRadius: "var(--radius-md)", background: "var(--color-surface-hover)" }}>
                <div>
                  <StatusBadge label={p.scene_key} variant="info" />
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginLeft: "var(--space-sm)" }}>
                    提交时间：{new Date(p.submitted_at).toLocaleString()}
                  </span>
                </div>
                <DangerConfirm
                  trigger={<button className="btn btn-sm btn-danger">删除</button>}
                  title="删除偏好"
                  message="确定删除此偏好吗？此操作不可撤销。"
                  confirmLabel="删除"
                  onConfirm={() => handleDelete(p.id)}
                />
              </div>
            ))}
          </div>
        )}
        <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-sm)" }}>
          出于隐私保护，不展示偏好正文，只显示提交元数据。
        </p>
      </div>

      {/* Submit new preference */}
      {success ? (
        <div className="card" style={{ borderColor: "var(--color-success)", background: "var(--color-success-light)" }}>
          <p style={{ color: "var(--color-success)", fontWeight: "var(--font-weight-medium)" }}>
            ✓ 偏好已提交成功。出于隐私保护，页面不会展示偏好正文。
          </p>
          <button className="btn" onClick={() => setSuccess(false)} style={{ marginTop: "var(--space-sm)" }}>
            继续提交
          </button>
        </div>
      ) : (
        <div className="card">
          <h2 style={{ fontSize: "var(--font-size-lg)", marginBottom: "var(--space-md)" }}>提交新偏好</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
            <div>
              <label htmlFor="pref-budget" style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                预算范围（元）
              </label>
              <input id="pref-budget" className="input" placeholder="例如：20-50" value={budget} onChange={(e) => setBudget(e.target.value)} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                饮食限制
              </label>
              <div style={{ display: "flex", gap: "var(--space-sm)", flexWrap: "wrap" }}>
                {["素食", "清真", "不吃辣", "无麸质", "无"].map((d) => (
                  <label key={d} style={{ display: "flex", alignItems: "center", gap: "var(--space-xs)", fontSize: "var(--font-size-sm)" }}>
                    <input type="checkbox" checked={dietary.includes(d)} onChange={(e) => { if (e.target.checked) setDietary([...dietary, d]); else setDietary(dietary.filter((x) => x !== d)); }} />
                    {d}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label htmlFor="pref-time" style={{ display: "block", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-xs)", fontWeight: "var(--font-weight-medium)" }}>
                偏好时间
              </label>
              <select id="pref-time" className="input" value={timeSlot} onChange={(e) => setTimeSlot(e.target.value)}>
                <option value="">请选择时间...</option>
                <option value="17:00">17:00 - 18:00</option>
                <option value="18:00">18:00 - 19:00</option>
                <option value="19:00">19:00 - 20:00</option>
                <option value="20:00">20:00 - 21:00</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting || (!budget && dietary.length === 0 && !timeSlot)}>
              {submitting ? "提交中..." : "提交偏好"}
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
