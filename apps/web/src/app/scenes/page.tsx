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
    title: "宿舍聚餐",
    description: "和舍友协商聚餐计划。提交私密偏好后，系统会生成聚合餐厅推荐。",
    status: "available",
    privacySummary: "私密偏好会加密保存，仅用于聚合计算。其他成员只能看到聚合结果。",
    dataTypes: ["饮食限制", "预算范围", "时间偏好", "位置限制"],
  },
  {
    key: "study_group",
    title: "学习小组",
    description: "根据课程与时间安排寻找合适的学习伙伴。",
    status: "concept",
    privacySummary: "课程安排仅用于匹配学习伙伴。",
    dataTypes: ["课程安排", "学习偏好"],
  },
  {
    key: "room_share",
    title: "宿舍分账",
    description: "和室友一起分摊宿舍开销。",
    status: "concept",
    privacySummary: "开销数据仅用于分账计算。",
    dataTypes: ["开销项目", "支付偏好"],
  },
];

function ScenesContent() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-lg)" }}>
      <h1 style={{ fontSize: "var(--font-size-xl)" }}>场景</h1>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "var(--space-md)" }}>
        {SCENES.map((scene) => (
          <div key={scene.key} className="card" style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>{scene.title}</h3>
              <StatusBadge
                label={scene.status === "available" ? "可用" : "即将推出"}
                variant={scene.status === "available" ? "success" : "default"}
              />
            </div>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
              {scene.description}
            </p>

            <div style={{ background: "var(--color-privacy-light)", padding: "var(--space-sm)", borderRadius: "var(--radius-md)" }}>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-privacy)", fontWeight: "var(--font-weight-medium)", marginBottom: "var(--space-xs)" }}>
                🔒 隐私
              </p>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-primary)" }}>
                {scene.privacySummary}
              </p>
            </div>

            <div>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", marginBottom: "var(--space-xs)" }}>
                使用的数据：
              </p>
              <div style={{ display: "flex", gap: "var(--space-xs)", flexWrap: "wrap" }}>
                {scene.dataTypes.map((dt) => (
                  <span key={dt} className="badge">{dt}</span>
                ))}
              </div>
            </div>

            {scene.status === "available" ? (
              <Link href={scene.key === "dorm_dinner" ? "/scenes/dinner" : "/scenes"} className="btn btn-primary" style={{ marginTop: "var(--space-sm)", textAlign: "center" }}>
                进入场景
              </Link>
            ) : (
              <button className="btn" disabled style={{ marginTop: "var(--space-sm)" }}>
                即将推出
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
