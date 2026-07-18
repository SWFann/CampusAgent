"use client";

/**
 * Status badge component.
 * Displays a colored badge with a label.
 */
type BadgeVariant = "success" | "warning" | "danger" | "info" | "privacy" | "default";

const variantClasses: Record<BadgeVariant, string> = {
  success: "badge-success",
  warning: "badge-warning",
  danger: "badge-danger",
  info: "badge-info",
  privacy: "badge-privacy",
  default: "",
};

const LABELS: Record<string, string> = {
  SYSTEM_ADMIN: "系统管理员",
  ADMIN: "管理员",
  SUPER_ADMIN: "超级管理员",
  STUDENT: "学生",
  USER: "用户",
  OWNER: "负责人",
  MEMBER: "成员",
  GUEST: "访客",
  PRIVATE: "私聊",
  GROUP: "群聊",
  ORG_GROUP: "组织群聊",
  SCENE: "场景",
  TEXT: "文本",
  IMAGE: "图片",
  FILE: "文件",
  SYSTEM: "系统",
  AGENT_PUBLIC: "智能体公开消息",
  SCENE_CARD: "场景卡片",
  VOTE: "投票",
  PROPOSAL: "方案",
  RESULT: "结果",
  PRIVACY_NOTICE: "隐私提示",
  ACTIVE: "启用",
  ARCHIVED: "已归档",
  LEFT: "已离开",
  REMOVED: "已移除",
  INACTIVE: "停用",
  DELETED: "已删除",
  PENDING: "待处理",
  FAILED: "失败",
  SUCCESS: "成功",
  READY: "就绪",
  DEGRADED: "降级",
  HIGH: "高敏感",
  MEDIUM: "中敏感",
  LOW: "低敏感",
  PREFERENCE: "偏好",
  FACT: "事实",
  CONTEXT: "上下文",
  FEEDBACK: "反馈",
  available: "可用",
  concept: "规划中",
  enabled: "已启用",
  disabled: "已停用",
  success: "成功",
  failed: "失败",
  revoked: "已撤销",
  granted: "已授权",
  dorm_dinner: "宿舍聚餐",
  L0: "仅建议",
  L1: "需确认",
  L2: "半自动",
  L3: "自动执行",
};

export function displayLabel(label: string): string {
  return LABELS[label] ?? label;
}

export function StatusBadge({
  label,
  variant = "default",
}: {
  label: string;
  variant?: BadgeVariant;
}) {
  const className = variantClasses[variant] || "";
  return (
    <span className={`badge ${className}`} role="status">
      {displayLabel(label)}
    </span>
  );
}
