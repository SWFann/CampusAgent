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
import type { SceneCandidate } from "@/lib/api/types";

interface VoteStatus {
  candidate_key: string;
  has_voted: boolean;
}

interface ConfirmStatus {
  confirmed: boolean;
  confirmed_candidate?: string;
}

function sanitizeReason(reason: string): string {
  // Remove any personal attribution patterns like "Zhang San doesn't eat spicy"
  const patterns = [
    /[A-Z][a-z]+\s+(doesn't|don't|can't|won't)\s+/g,
    /[\u4e00-\u9fff]{2,4}(不吃|不能吃|不吃辣|过敏)/g,
    /\b\w+\s+prefers?\s+/gi,
    /\b\w+\s+allergic\s+to\s+/gi,
  ];
  let sanitized = reason;
  for (const p of patterns) {
    sanitized = sanitized.replace(p, "多位成员");
  }
  return sanitized;
}

function DinnerResultContent() {
  const [voting, setVoting] = useState<string | null>(null);

  const { data: candidates, loading, error, reload } = useAsync<SceneCandidate[]>(
    async () => apiGet("/scenes/dorm_dinner/candidates"),
    [],
  );

  const { data: voteStatus } = useAsync<VoteStatus[]>(
    async () => apiGet("/scenes/dorm_dinner/votes"),
    [],
  );

  const { data: confirmStatus } = useAsync<ConfirmStatus>(
    async () => apiGet("/scenes/dorm_dinner/confirmation"),
    [],
  );

  const handleVote = async (candidateKey: string) => {
    setVoting(candidateKey);
    try {
      await apiPost("/scenes/dorm_dinner/votes", { candidate_key: candidateKey });
      reload();
    } catch {
      // Error handled by state
    } finally {
      setVoting(null);
    }
  };

  const handleConfirm = async (candidateKey: string) => {
    await apiPost("/scenes/dorm_dinner/confirmation", { candidate_key: candidateKey });
    reload();
  };

  const handleRevokeVote = async (candidateKey: string) => {
    await apiDelete(`/scenes/dorm_dinner/votes/${candidateKey}`);
    reload();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>聚餐结果</h1>

      {/* Privacy notice: results show only aggregated reasons */}
      <PrivacyNotice title="仅展示聚合结果">
        <p>这里仅展示聚合推荐，不展示任何个人偏好。</p>
      </PrivacyNotice>

      {loading && <LoadingState message="正在加载结果..." />}
      {error && <ErrorState message="加载结果失败。" />}
      {candidates && candidates.length === 0 && (
        <EmptyState title="暂无候选方案" description="参与者提交偏好后，候选方案会显示在这里。" />
      )}

      {confirmStatus?.confirmed && (
        <div className="card" style={{ borderColor: "var(--color-success)", background: "var(--color-success-light)" }}>
          <p style={{ color: "var(--color-success)", fontWeight: "var(--font-weight-semibold)" }}>
            ✓ 已确认聚餐方案： {confirmStatus.confirmed_candidate}
          </p>
        </div>
      )}

      {candidates && candidates.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
          {candidates.map((cand, idx) => {
            const userVote = voteStatus?.find((v) => v.candidate_key === cand.candidate_key);
            const hasVoted = userVote?.has_voted ?? false;
            return (
              <div key={cand.candidate_key} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", gap: "var(--space-sm)", alignItems: "center", marginBottom: "var(--space-xs)" }}>
                      <span style={{ fontSize: "var(--font-size-lg)", fontWeight: "var(--font-weight-bold)" }}>#{idx + 1}</span>
                      <h3>{cand.display_name}</h3>
                      <StatusBadge label={`得分：${cand.aggregate_score.toFixed(1)}`} variant="info" />
                    </div>

                    {/* Sanitized public reasons - no personal attribution */}
                    {cand.public_reasons && cand.public_reasons.length > 0 && (
                      <ul style={{ marginLeft: "var(--space-lg)", fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
                        {cand.public_reasons.map((reason, i) => (
                          <li key={i}>{sanitizeReason(reason)}</li>
                        ))}
                      </ul>
                    )}

                    {cand.public_metadata && (
                      <div style={{ display: "flex", gap: "var(--space-xs)", flexWrap: "wrap", marginTop: "var(--space-sm)" }}>
                        {Object.entries(cand.public_metadata).map(([k, v]) => (
                          <span key={k} className="badge">{k}: {String(v)}</span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)", alignItems: "flex-end" }}>
                    {hasVoted ? (
                      <DangerConfirm
                        trigger={<button className="btn btn-sm">撤销投票</button>}
                        title="撤销投票"
                        message="确定撤销对此候选方案的投票吗？"
                        confirmLabel="撤销"
                        onConfirm={() => handleRevokeVote(cand.candidate_key)}
                      />
                    ) : (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => handleVote(cand.candidate_key)}
                        disabled={voting === cand.candidate_key}
                      >
                        {voting === cand.candidate_key ? "投票中..." : "投票"}
                      </button>
                    )}
                    {!confirmStatus?.confirmed && (
                      <button
                        className="btn btn-sm"
                        onClick={() => handleConfirm(cand.candidate_key)}
                      >
                        确认方案
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function DinnerResultPage() {
  return (
    <AppShell requireAuth>
      <DinnerResultContent />
    </AppShell>
  );
}
