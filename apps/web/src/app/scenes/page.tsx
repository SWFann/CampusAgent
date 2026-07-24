"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app/AppShell";
import { apiGet, apiPost } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { useAsync } from "@/lib/useAsync";

interface CampusGroup {
  id: string;
  name: string;
  type: string;
  member_count: number;
  role?: string | null;
  current_role?: string | null;
  current_membership_status?: string | null;
}

interface GroupResponse { organizations: CampusGroup[] }

interface SceneInstance {
  id: string;
  scene_key: string;
  organization_id?: string | null;
  status: string;
  current_phase: string;
  created_by: string;
  public_context?: Record<string, unknown> | null;
  expires_at?: string | null;
  created_at: string;
  updated_at: string;
  participant_count: number;
  submitted_count: number;
  participant_status?: string | null;
  is_creator: boolean;
}

interface SceneResponse { scenes: SceneInstance[]; total: number }
interface Candidate { id: string; candidate_key: string; display_name: string; public_reason?: string | null; aggregate_score?: number | null; rank?: number | null; status: string }
interface CandidateResponse { candidates: Candidate[]; total: number }
interface ResultResponse { public_summary?: string | null; participant_count: number; submitted_count: number }
interface SubmissionStatus { has_submitted: boolean }

type SceneFilter = "todo" | "active" | "confirming" | "completed";
type RequiredTaskStatus = "WAITING_INPUT" | "WAITING_INTENT_CONFIRM" | "WAITING_MATCH" | "NEGOTIATING" | "ACTION_REQUIRED" | "CONFIRMING" | "REMATCH_REQUIRED" | "SCHOOL_REVIEW" | "COMPLETED";

interface SceneTemplate {
  key: string;
  icon: string;
  title: string;
  description: string;
  output: string;
  defaultOptions: string[];
  tone: "green" | "blue" | "amber";
  href?: string;
  demo?: boolean;
}

const REQUIRED_DORM_TASK: SceneTemplate = { key: "dorm_roommate_demo", icon: "舍", title: "新生宿舍共识安排", description: "在学生主动授权的生活偏好范围内，由多个 Agent 协商住宿建议并交由本人和学校确认。", output: "住宿建议与寝室共识", defaultOptions: [], tone: "green", href: "/scenes/dormitory-match", demo: true };

const CREATE_TEMPLATES: SceneTemplate[] = [
  { key: "dorm_dinner", icon: "餐", title: "吃饭聚餐投票", description: "收集时间、预算、位置和饮食限制，形成可确认的聚餐方案。", output: "聚餐地点与时间方案", defaultOptions: ["番禺广场附近", "校内食堂", "大学城商圈"], tone: "amber", href: "/scenes/dinner" },
  { key: "time_poll", icon: "时", title: "共同时间协调", description: "收集成员可用时间，快速找到最多人可以参加的时段。", output: "共同可用时间", defaultOptions: ["周四 19:00", "周五 16:00", "周六 10:00"], tone: "blue" },
  { key: "task_claim", icon: "任", title: "任务分工认领", description: "把集体工作拆分成任务，由成员自主认领并汇总进度。", output: "任务负责人和进度", defaultOptions: ["资料整理", "现场协调", "成果汇报"], tone: "green" },
];
const TEMPLATES: SceneTemplate[] = [REQUIRED_DORM_TASK, ...CREATE_TEMPLATES];
const REQUIRED_TASK_STORAGE_KEY = "campusagent:dorm-required-task";

const REQUIRED_TASK_STATES: Record<RequiredTaskStatus, { label: string; note: string; action: string; progress: number; urgent?: boolean; complete?: boolean }> = {
  WAITING_INPUT: { label: "待表达需求", note: "请先确认个人授权范围并填写室友偏好", action: "立即办理", progress: 1 },
  WAITING_INTENT_CONFIRM: { label: "待确认 Agent 理解", note: "确认 Agent 将如何代表你参与匹配", action: "继续确认", progress: 2, urgent: true },
  WAITING_MATCH: { label: "等待候选成员", note: "系统正在寻找符合硬性条件的候选室友", action: "查看进度", progress: 3 },
  NEGOTIATING: { label: "Agent 协商中", note: "多位 Agent 正在形成可供本人确认的组合", action: "查看协商", progress: 4 },
  ACTION_REQUIRED: { label: "有新增条件待决定", note: "其他成员提出了补充条件，需要你本人决定", action: "立即处理", progress: 4, urgent: true },
  CONFIRMING: { label: "待确认室友组合", note: "Agent 已形成建议，请决定是否接受", action: "确认结果", progress: 5, urgent: true },
  REMATCH_REQUIRED: { label: "已退出本轮 · 待重新匹配", note: "必办任务仍未完成，可重新匹配或申请人工协调", action: "重新匹配", progress: 3, urgent: true },
  SCHOOL_REVIEW: { label: "学校审核中", note: "所有成员已确认，等待住宿工作组审核", action: "查看进度", progress: 6 },
  COMPLETED: { label: "已完成", note: "宿舍安排已经确认，可查看寝室信息", action: "查看结果", progress: 6, complete: true },
};

const STAGES = [
  { status: "DRAFT", label: "设置" },
  { status: "INVITING", label: "邀请" },
  { status: "COLLECTING_PRIVATE_INPUT", label: "参与" },
  { status: "GENERATING_CANDIDATES", label: "整理" },
  { status: "VOTING", label: "表决" },
  { status: "CONFIRMING", label: "确认" },
  { status: "COMPLETED", label: "完成" },
];

function groupIcon(type: string) {
  return ({ COURSE: "课", CLASS: "班", DORM: "舍", CLUB: "社", TEAM: "项", LAB: "实", COLLEGE: "院" } as Record<string, string>)[type] ?? "群";
}

function roleLabel(role?: string | null) {
  return ({ OWNER: "负责人", ADMIN: "管理员", MEMBER: "成员", GUEST: "观察成员" } as Record<string, string>)[role ?? ""] ?? "成员";
}

function sceneTemplate(scene: SceneInstance) {
  return TEMPLATES.find((item) => item.key === scene.scene_key) ?? CREATE_TEMPLATES[0];
}

function sceneTitle(scene: SceneInstance) {
  return String(scene.public_context?.title || sceneTemplate(scene).title);
}

function statusLabel(status: string) {
  return ({ DRAFT: "草稿", INVITING: "等待成员接受", COLLECTING_PRIVATE_INPUT: "正在参与", GENERATING_CANDIDATES: "Agent整理中", VOTING: "成员表决", CONFIRMING: "等待确认", COMPLETED: "已完成", CANCELLED: "已取消", EXPIRED: "已过期", FAILED: "处理失败" } as Record<string, string>)[status] ?? status;
}

function isTodo(scene: SceneInstance) {
  return scene.participant_status === "INVITED" || scene.status === "COLLECTING_PRIVATE_INPUT" || (scene.is_creator && ["DRAFT", "VOTING", "CONFIRMING"].includes(scene.status));
}

function formatDeadline(value?: string | null) {
  if (!value) return "未设置截止时间";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function ScenesContent() {
  const { user } = useAuth();
  const { data: groupData, loading: groupLoading } = useAsync<GroupResponse>(async () => user ? apiGet(`/users/${user.id}/organizations`) : { organizations: [] }, [user?.id]);
  const { data: sceneData, loading: sceneLoading, reload: reloadScenes } = useAsync<SceneResponse>(() => apiGet("/scenes/mine"), []);
  const groups = useMemo(() => (groupData?.organizations ?? []).filter((group) => (group.current_membership_status ?? "ACTIVE") === "ACTIVE"), [groupData]);

  const [groupId, setGroupId] = useState("");
  const [filter, setFilter] = useState<SceneFilter>("todo");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [showDetail, setShowDetail] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createStep, setCreateStep] = useState(1);
  const [templateKey, setTemplateKey] = useState(CREATE_TEMPLATES[0].key);
  const [createGroupId, setCreateGroupId] = useState("");
  const [title, setTitle] = useState("");
  const [deadline, setDeadline] = useState("");
  const [optionsText, setOptionsText] = useState(CREATE_TEMPLATES[0].defaultOptions.join("\n"));
  const [anonymous, setAnonymous] = useState(false);
  const [agentEnabled, setAgentEnabled] = useState(true);
  const [creating, setCreating] = useState(false);
  const [acting, setActing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [requiredTaskStatus, setRequiredTaskStatus] = useState<RequiredTaskStatus>("WAITING_INPUT");

  useEffect(() => {
    const readRequiredTask = () => {
      try {
        const stored = JSON.parse(window.localStorage.getItem(REQUIRED_TASK_STORAGE_KEY) || "null") as { status?: RequiredTaskStatus } | null;
        if (stored?.status && REQUIRED_TASK_STATES[stored.status]) setRequiredTaskStatus(stored.status);
      } catch {
        setRequiredTaskStatus("WAITING_INPUT");
      }
    };
    readRequiredTask();
    window.addEventListener("focus", readRequiredTask);
    return () => window.removeEventListener("focus", readRequiredTask);
  }, []);

  useEffect(() => {
    if (!groups.length || groupId) return;
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("organization");
    const initial = groups.find((group) => group.id === requested)?.id ?? groups[0].id;
    setGroupId(initial);
    setCreateGroupId(initial);
  }, [groupId, groups]);

  const groupScenes = useMemo(() => (sceneData?.scenes ?? []).filter((scene) => {
    if (scene.scene_key === REQUIRED_DORM_TASK.key) return false;
    if (scene.organization_id !== groupId) return false;
    const keyword = search.trim().toLowerCase();
    if (keyword && !`${sceneTitle(scene)} ${statusLabel(scene.status)}`.toLowerCase().includes(keyword)) return false;
    if (filter === "todo") return isTodo(scene);
    if (filter === "completed") return scene.status === "COMPLETED";
    if (filter === "confirming") return ["VOTING", "CONFIRMING"].includes(scene.status);
    return !["DRAFT", "COMPLETED", "CANCELLED", "EXPIRED", "FAILED"].includes(scene.status);
  }), [filter, groupId, sceneData, search]);

  const selectedGroup = groups.find((group) => group.id === groupId) ?? groups[0] ?? null;
  const selected = groupScenes.find((scene) => scene.id === selectedId) ?? groupScenes[0] ?? null;
  const template = selected ? sceneTemplate(selected) : CREATE_TEMPLATES[0];
  const createTemplate = CREATE_TEMPLATES.find((item) => item.key === templateKey) ?? CREATE_TEMPLATES[0];
  const createGroup = groups.find((group) => group.id === createGroupId) ?? selectedGroup;
  const currentStage = selected ? Math.max(0, STAGES.findIndex((stage) => stage.status === selected.status)) : 0;
  const publicOptions = selected && Array.isArray(selected.public_context?.options) ? selected.public_context.options.map(String) : [];
  const requiredTask = REQUIRED_TASK_STATES[requiredTaskStatus];

  const { data: submissionStatus, reload: reloadSubmission } = useAsync<SubmissionStatus>(async () => selected?.status === "COLLECTING_PRIVATE_INPUT" && selected.participant_status === "ACCEPTED" ? apiGet(`/scenes/${selected.id}/submissions/status`) : { has_submitted: false }, [selected?.id, selected?.status, selected?.participant_status]);
  const { data: candidateData, reload: reloadCandidates } = useAsync<CandidateResponse>(async () => selected && ["VOTING", "CONFIRMING", "COMPLETED"].includes(selected.status) ? apiGet(`/scenes/${selected.id}/candidates`) : { candidates: [], total: 0 }, [selected?.id, selected?.status]);
  const { data: resultData, reload: reloadResult } = useAsync<ResultResponse | null>(async () => selected?.status === "COMPLETED" ? apiGet(`/scenes/${selected.id}/result`) : null, [selected?.id, selected?.status]);

  const refresh = async () => {
    await Promise.all([reloadScenes(), reloadSubmission(), reloadCandidates(), reloadResult()]);
  };

  const selectGroup = (nextId: string) => {
    setGroupId(nextId);
    setCreateGroupId(nextId);
    setSelectedId("");
    setShowDetail(false);
    setSearch("");
    setMessage(null);
  };

  const openCreate = () => {
    setCreateStep(1);
    setTemplateKey(CREATE_TEMPLATES[0].key);
    setCreateGroupId(groupId || groups[0]?.id || "");
    setTitle("");
    setDeadline("");
    setOptionsText(CREATE_TEMPLATES[0].defaultOptions.join("\n"));
    setMessage(null);
    setShowCreate(true);
  };

  const chooseTemplate = (next: SceneTemplate) => {
    setTemplateKey(next.key);
    setOptionsText(next.defaultOptions.join("\n"));
  };

  const createScene = async (event: FormEvent) => {
    event.preventDefault();
    if (createStep === 1 && createTemplate.demo && createTemplate.href) {
      window.location.href = createTemplate.href;
      return;
    }
    if (createStep < 4) {
      setCreateStep((step) => step + 1);
      return;
    }
    if (!createGroup || !user) return;
    setCreating(true);
    try {
      const options = optionsText.split("\n").map((item) => item.trim()).filter(Boolean);
      const created = await apiPost<SceneInstance>("/scenes", {
        scene_key: createTemplate.key,
        organization_id: createGroup.id,
        participant_user_ids: [user.id],
        expires_at: deadline ? new Date(deadline).toISOString() : null,
        idempotency_key: `web-${createGroup.id}-${Date.now()}`,
        public_context: { title: title.trim() || `${createGroup.name} · ${createTemplate.title}`, template_key: createTemplate.key, options, anonymous, agent_enabled: agentEnabled, organization_name: createGroup.name },
      });
      await reloadScenes();
      setGroupId(createGroup.id);
      setFilter("todo");
      setSelectedId(created.id);
      setShowDetail(true);
      setShowCreate(false);
      setMessage("协作草稿已经保存，可以检查后发布。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "创建失败，请稍后重试。");
    } finally {
      setCreating(false);
    }
  };

  const runAction = async (action: string) => {
    if (!selected) return;
    setActing(true);
    setMessage(null);
    try {
      if (action === "accept") await apiPost(`/scenes/${selected.id}/accept`);
      else if (action === "decline") await apiPost(`/scenes/${selected.id}/decline`);
      else if (action === "publish") {
        await apiPost(`/scenes/${selected.id}/transition`, { action: "publish" });
        await apiPost(`/scenes/${selected.id}/transition`, { action: "start_collecting" });
      } else if (action === "process") await apiPost(`/scenes/${selected.id}/process`);
      else await apiPost(`/scenes/${selected.id}/transition`, { action });
      await refresh();
      setMessage(action === "publish" ? "协作已发布，成员现在可以参与。" : action === "accept" ? "你已加入本次协作。" : action === "confirm" ? "结果已经由负责人确认并归档。" : "协作状态已更新。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "操作失败，请稍后重试。");
    } finally {
      setActing(false);
    }
  };

  const submitChoices = async () => {
    if (!selected || !selectedOptions.length) return;
    setActing(true);
    try {
      await apiPost(`/scenes/${selected.id}/submissions`, { preferences: { selections: selectedOptions }, save_to_long_term_memory: false });
      await refresh();
      setMessage("你的选择已提交。原始选择仅用于本次协作，不会写入个人记忆。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "提交失败，请稍后重试。");
    } finally {
      setActing(false);
    }
  };

  const castVote = async (candidateId: string) => {
    if (!selected) return;
    setActing(true);
    try {
      await apiPost(`/scenes/${selected.id}/votes`, { candidate_id: candidateId, vote_value: "APPROVE", idempotency_key: `web-vote-${selected.id}-${candidateId}` });
      setMessage("投票已记录，你仍可在截止前调整选择。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "投票失败，请稍后重试。");
    } finally {
      setActing(false);
    }
  };

  const primaryAction = () => {
    if (!selected) return null;
    if (selected.participant_status === "INVITED") return <><button type="button" onClick={() => runAction("decline")}>谢绝</button><button className="is-primary" type="button" onClick={() => runAction("accept")}>接受并加入 <span>→</span></button></>;
    if (selected.status === "DRAFT" && selected.is_creator) return <button className="is-primary" type="button" onClick={() => runAction("publish")}>发布协作 <span>→</span></button>;
    if (selected.status === "COLLECTING_PRIVATE_INPUT" && template.href) return <Link className="is-primary" href={template.href}>参加协作 <span>→</span></Link>;
    if (selected.status === "COLLECTING_PRIVATE_INPUT" && selected.is_creator && submissionStatus?.has_submitted) return <button className="is-primary" type="button" onClick={() => runAction("process")}>结束收集并整理 <span>→</span></button>;
    if (selected.status === "VOTING" && selected.is_creator) return <button className="is-primary" type="button" onClick={() => runAction("voting_complete")}>结束表决 <span>→</span></button>;
    if (selected.status === "CONFIRMING" && selected.is_creator) return <button className="is-primary" type="button" onClick={() => runAction("confirm")}>确认并归档结果 <span>→</span></button>;
    return null;
  };

  return (
    <>
      <section className={`scene-hub scene-library scene-live-library has-required-task${showDetail ? " is-detail-open" : ""}`} aria-label="协作空间">
        <header className="scene-hub-header">
          <div className="scene-hub-title"><span>群体协作中心</span><h1>协作空间</h1><p>从待我参与开始，和群体一起形成可确认、可追溯的结果。</p></div>
          <label className="scene-search"><span aria-hidden="true">⌕</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索当前群体的协作" />{search && <button type="button" onClick={() => setSearch("")} aria-label="清空搜索">×</button>}</label>
          <button className="scene-create-button" type="button" onClick={openCreate} disabled={!groups.length}><span>＋</span>创建协作</button>
        </header>

        <section className={`scene-required-task${requiredTask.urgent ? " is-urgent" : ""}${requiredTask.complete ? " is-complete" : ""}`} aria-labelledby="required-dorm-title">
          <header><span>学校要求完成</span><small>2026级新生 · 1 项必办</small></header>
          <div className="scene-required-task-main">
            <span className="scene-required-icon">舍<i>校</i></span>
            <div className="scene-required-copy"><div><em>暨南大学住宿工作组发布</em><b>{requiredTask.label}</b></div><h2 id="required-dorm-title">新生宿舍共识安排</h2><p>{requiredTask.note}</p></div>
            <div className="scene-required-progress" aria-label={`已进行到第 ${requiredTask.progress} 步，共 6 步`}><span><small>办理进度</small><strong>{requiredTask.progress}/6</strong></span><i><b style={{ width: `${requiredTask.progress / 6 * 100}%` }} /></i></div>
            <dl><div><dt>截止时间</dt><dd>8月20日 18:00</dd></div><div><dt>参与原则</dt><dd>可退出单轮匹配</dd></div></dl>
            <Link href="/scenes/dormitory-match">{requiredTask.action}<span>→</span></Link>
          </div>
          <footer><span>必办的是完成住宿安排流程，不是强制接受某组室友。</span><b>退出一轮后任务仍保留，可重新匹配或申请人工协调</b></footer>
        </section>

        <div className="scene-hub-body">
          <aside className="scene-category-nav scene-group-nav" aria-label="我加入的群体">
            <header><strong>我的群体</strong><small>选择协作发生在哪里</small></header>
            <div>{groups.map((group) => {
              const count = (sceneData?.scenes ?? []).filter((scene) => scene.organization_id === group.id).length;
              return <button key={group.id} className={groupId === group.id ? "is-active" : ""} type="button" onClick={() => selectGroup(group.id)}><span>{groupIcon(group.type)}</span><span className="scene-group-nav-copy"><strong>{group.name}</strong><small>{roleLabel(group.role ?? group.current_role)} · {group.member_count}人</small></span><i>{count}</i></button>;
            })}</div>
            {!groupLoading && !groups.length && <p className="scene-group-empty">你还没有加入可协作的群体。</p>}
          </aside>

          <section className="scene-content-panel" aria-label={`${selectedGroup?.name ?? "群体"}的协作库`}>
            <label className="scene-mobile-group-select"><span>切换群体</span><select value={groupId} onChange={(event) => selectGroup(event.target.value)}>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
            <header><div><span>协作库 · {selectedGroup ? roleLabel(selectedGroup.role ?? selectedGroup.current_role) : ""}</span><h2>{selectedGroup?.name ?? "选择一个群体"}</h2></div><small>{groupScenes.length} 项</small></header>
            <div className="scene-library-tabs" role="tablist" aria-label="协作状态筛选">{([{ id: "todo", label: "待我参与" }, { id: "active", label: "进行中" }, { id: "confirming", label: "待确认" }, { id: "completed", label: "已完成" }] as { id: SceneFilter; label: string }[]).map((item) => <button key={item.id} className={filter === item.id ? "is-active" : ""} type="button" onClick={() => { setFilter(item.id); setSelectedId(""); setShowDetail(false); }}>{item.label}</button>)}</div>
            <div className="scene-space-list">{groupScenes.map((scene) => {
              const itemTemplate = sceneTemplate(scene);
              return <button key={scene.id} type="button" className={selected?.id === scene.id ? "is-selected" : ""} onClick={() => { setSelectedId(scene.id); setShowDetail(true); setMessage(null); }}><span className={`scene-icon is-${itemTemplate.tone}`}>{itemTemplate.icon}</span><span className="scene-space-copy"><span><strong>{sceneTitle(scene)}</strong><em className={`is-${scene.status === "COMPLETED" ? "completed" : scene.status === "DRAFT" ? "draft" : "active"}`}>{statusLabel(scene.status)}</em></span><small>{itemTemplate.title} · {scene.submitted_count}/{scene.participant_count} 人已提交</small><span className="scene-space-meta"><b>{isTodo(scene) ? "需要你处理" : formatDeadline(scene.expires_at)}</b><time>{formatDeadline(scene.expires_at)}</time></span></span></button>;
            })}{!sceneLoading && !groupScenes.length && <div className="scene-empty-state"><span>{filter === "todo" ? "✓" : "◎"}</span><strong>{filter === "todo" ? "目前没有等待你处理的自主协作" : "这个分类还没有协作"}</strong><p>学校必办协作显示在页面顶部；这里可以查看或创建群体自主协作。</p></div>}</div>
          </section>

          {selected ? <section className="scene-detail" aria-label="协作详情">
            <header className="scene-detail-header"><button className="scene-mobile-back" type="button" onClick={() => setShowDetail(false)} aria-label="返回协作列表">←</button><span className={`scene-icon is-${template.tone}`}>{template.icon}</span><div><span>{selectedGroup?.name}</span><h2>{sceneTitle(selected)}</h2><small>{template.title} · {statusLabel(selected.status)}</small></div><button type="button" aria-label="收藏协作">☆</button></header>
            <div className="scene-detail-scroll">
              {message && <p className="scene-live-message">{message}</p>}
              <section className="scene-purpose-card"><header><div><span>当前阶段</span><strong>{statusLabel(selected.status)}</strong></div><em>{selected.submitted_count}/{selected.participant_count} 已提交</em></header><p>{String(selected.public_context?.summary || template.description)}</p><div className="scene-latest"><span>截止</span><p>{formatDeadline(selected.expires_at)}</p></div></section>
              <ol className="scene-stage-track">{STAGES.map((stage, index) => <li key={stage.status} className={index < currentStage ? "is-done" : index === currentStage ? "is-current" : ""}><span>{index < currentStage ? "✓" : index + 1}</span><small>{stage.label}</small></li>)}</ol>

              {selected.status === "COLLECTING_PRIVATE_INPUT" && !template.href && selected.participant_status === "ACCEPTED" && <section className="scene-participation-panel"><header><div><span>我的参与</span><h3>{template.key === "time_poll" ? "选择所有你可以参加的时间" : "选择你愿意认领的任务"}</h3></div><small>{submissionStatus?.has_submitted ? "已经提交，可再次更新" : "尚未提交"}</small></header><div>{publicOptions.map((option) => <label key={option} className={selectedOptions.includes(option) ? "is-selected" : ""}><input type="checkbox" checked={selectedOptions.includes(option)} onChange={() => setSelectedOptions((items) => items.includes(option) ? items.filter((item) => item !== option) : [...items, option])} /><span>{option}</span><i>✓</i></label>)}</div><button type="button" onClick={submitChoices} disabled={!selectedOptions.length || acting}>{submissionStatus?.has_submitted ? "更新我的提交" : "提交我的选择"}</button></section>}

              {["VOTING", "CONFIRMING", "COMPLETED"].includes(selected.status) && <section className="scene-candidate-panel"><header><div><span>{selected.status === "COMPLETED" ? "协作结果" : "候选结果"}</span><h3>{template.output}</h3></div></header>{candidateData?.candidates.length ? <div>{candidateData.candidates.sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99)).map((candidate) => <article key={candidate.id}><span>{candidate.rank ? candidate.rank : "候选"}</span><div><strong>{candidate.display_name}</strong><small>{candidate.public_reason || "由 Agent 根据本次协作提交汇总"}</small></div>{selected.status === "VOTING" && <button type="button" onClick={() => castVote(candidate.id)} disabled={acting}>支持</button>}</article>)}</div> : <p>Agent 正在整理公开候选结果。</p>}{resultData?.public_summary && <aside><strong>负责人已确认</strong><p>{resultData.public_summary}</p></aside>}</section>}

              <section className="scene-result-card"><header><span>预期产出</span><strong>{template.output}</strong></header><p>Agent 只整理成员在本次协作中主动提交的信息，候选结果仍由成员表决并由负责人最终确认。</p></section>
              <aside className="scene-agent-boundary"><span>隐私边界</span><strong>群体协作不读取个人 Agent 私有记忆</strong><p>原始选择加密保存；负责人只能看到完成情况和聚合结果，不能查看个人私密提交。</p></aside>
            </div>
            <footer className="scene-detail-actions">{acting ? <button type="button" disabled>正在处理…</button> : primaryAction()}</footer>
          </section> : <section className="scene-detail scene-empty-detail"><span>◎</span><strong>选择一次协作</strong><p>查看阶段、完成你的参与，并追踪最终结果。</p></section>}
        </div>
      </section>

      {showCreate && <div className="scene-create-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setShowCreate(false)}><form className="scene-create-drawer" onSubmit={createScene}>
        <header><div><span>创建协作</span><h2>{createStep === 1 ? "选择内置场景" : createStep === 2 ? "选择所属群体" : createStep === 3 ? "设置参与规则" : "确认并保存草稿"}</h2></div><button type="button" onClick={() => setShowCreate(false)} aria-label="关闭创建协作空间">×</button></header>
        <div className="scene-create-progress" aria-label={`第 ${createStep} 步，共 4 步`}>{[1, 2, 3, 4].map((step) => <span key={step} className={step <= createStep ? "is-active" : ""} />)}</div>
        <div className="scene-create-content">
          {createStep === 1 && <><p className="scene-create-lead">创建群体自主发起的协作。学校必办事项由相应部门统一发布，不在这里创建。</p><div className="scene-create-template-grid scene-built-in-grid">{CREATE_TEMPLATES.map((item) => <button key={item.key} type="button" className={templateKey === item.key ? "is-selected" : ""} onClick={() => chooseTemplate(item)}><span className={`scene-icon is-${item.tone}`}>{item.icon}</span><div><strong>{item.title}</strong><small>{item.description}</small></div><i>✓</i></button>)}</div><aside className="scene-create-note"><strong>为什么没有宿舍安排？</strong><p>新生宿舍属于学校统一下发的必办协作，学生无需也不能自行创建。</p></aside></>}
          {createStep === 2 && <><div className="scene-create-group-list">{groups.map((group) => <button key={group.id} type="button" className={createGroupId === group.id ? "is-selected" : ""} onClick={() => setCreateGroupId(group.id)}><span>{groupIcon(group.type)}</span><div><strong>{group.name}</strong><small>{group.member_count}位成员 · {roleLabel(group.role ?? group.current_role)}</small></div><i>✓</i></button>)}</div><aside className="scene-create-note"><strong>协作与群体真实绑定</strong><p>创建后进入该群体的协作库，参与范围跟随当前有效成员关系。</p></aside></>}
          {createStep === 3 && <div className="scene-create-settings"><label><span>协作名称</span><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder={`${createGroup?.name ?? "群体"} · ${createTemplate.title}`} /></label><label><span>截止时间</span><input type="datetime-local" value={deadline} onChange={(event) => setDeadline(event.target.value)} /></label>{createTemplate.key !== "dorm_dinner" && <label><span>{createTemplate.key === "time_poll" ? "候选时间（每行一项）" : "待认领任务（每行一项）"}</span><textarea rows={5} value={optionsText} onChange={(event) => setOptionsText(event.target.value)} /></label>}<label className="scene-agent-toggle"><span><strong>允许匿名提交</strong><small>负责人能看到谁已完成，但不能读取个人原始选择。</small></span><input type="checkbox" checked={anonymous} onChange={(event) => setAnonymous(event.target.checked)} /></label><label className="scene-agent-toggle"><span><strong>启用场景 Agent</strong><small>仅使用本次协作的加密提交生成聚合候选结果。</small></span><input type="checkbox" checked={agentEnabled} onChange={(event) => setAgentEnabled(event.target.checked)} /></label></div>}
          {createStep === 4 && <div className="scene-create-review"><span className={`scene-icon is-${createTemplate.tone}`}>{createTemplate.icon}</span><h3>{title.trim() || `${createGroup?.name ?? "群体"} · ${createTemplate.title}`}</h3><p>{createTemplate.description}</p><dl><div><dt>所属群体</dt><dd>{createGroup?.name}</dd></div><div><dt>参与范围</dt><dd>群体当前有效成员</dd></div><div><dt>截止时间</dt><dd>{deadline ? formatDeadline(new Date(deadline).toISOString()) : "暂未设置"}</dd></div><div><dt>结果确认</dt><dd>创建者最终确认</dd></div></dl><aside><strong>先保存草稿，再正式发布</strong><p>发布后成员才会收到参与邀请，重要结果仍由负责人最终确认。</p></aside></div>}
          {message && <p className="scene-create-error">{message}</p>}
        </div>
        <footer><small>{createStep === 1 && createTemplate.demo ? "交互式场景演示" : `第 ${createStep} 步，共4步`}</small><div>{createStep > 1 && <button type="button" onClick={() => setCreateStep((step) => step - 1)}>上一步</button>}<button className="is-primary" type="submit" disabled={creating || (!createTemplate.demo && !createGroupId)}>{creating ? "保存中…" : createStep === 1 && createTemplate.demo ? "打开演示" : createStep === 4 ? "创建为草稿" : "继续"}</button></div></footer>
      </form></div>}
    </>
  );
}

export default function ScenesPage() {
  return <AppShell requireAuth><ScenesContent /></AppShell>;
}
