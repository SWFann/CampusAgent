"use client";

import Link from "next/link";
import { Dispatch, SetStateAction, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app/AppShell";

type DemoPhase = "intro" | "preferences" | "intent" | "waiting" | "negotiation" | "counter_proposal" | "proposal" | "no_consensus" | "withdrawn" | "confirmed";
type PreferenceKey = "schedule" | "environment" | "communication" | "social";
type Importance = "DEAL_BREAKER" | "MUST" | "PREFER" | "NEGOTIABLE" | "REFERENCE";

interface PreferenceRow { id: string; text: string; importance: Importance; source: "QUICK" | "CUSTOM" }
interface IntentPoint { id: string; original: string; interpretation: string; importance: Importance; source: string }

const PHASES = [
  { title: "表达需求", note: "选项与逐条补充" },
  { title: "确认意图", note: "确认 Agent 理解" },
  { title: "等待成员", note: "成员自主参加" },
  { title: "Agent 谈判", note: "最多三次" },
  { title: "确认室友", note: "所有成员确认" },
  { title: "学校审核", note: "责任人决定" },
];

const PREFERENCE_GROUPS: { key: PreferenceKey; index: string; title: string; description: string; options: string[] }[] = [
  { key: "schedule", index: "01", title: "生活作息", description: "选择最接近你的日常状态", options: ["早睡型", "正常作息", "晚睡型"] },
  { key: "environment", index: "02", title: "寝室环境", description: "你希望寝室大部分时间是什么氛围", options: ["喜欢安静", "适度交流", "喜欢热闹"] },
  { key: "communication", index: "03", title: "分歧沟通", description: "出现问题时，你更舒服的沟通方式", options: ["当面沟通", "群里沟通", "先由 Agent 协调"] },
  { key: "social", index: "04", title: "相处距离", description: "你期待怎样的室友关系", options: ["喜欢一起活动", "偶尔参与", "更需要个人空间"] },
];

const IMPORTANCE_OPTIONS: { value: Importance; label: string; short: string }[] = [
  { value: "DEAL_BREAKER", label: "明确不能接受", short: "硬性排除" },
  { value: "MUST", label: "必须满足", short: "必须满足" },
  { value: "PREFER", label: "尽量满足", short: "优先匹配" },
  { value: "NEGOTIABLE", label: "可以协商", short: "允许谈判" },
  { value: "REFERENCE", label: "仅作参考", short: "不影响筛选" },
];

const QUICK_ITEMS: { text: string; importance: Importance; category: string }[] = [
  { text: "不接受室友在寝室内吸烟", importance: "DEAL_BREAKER", category: "健康边界" },
  { text: "晚上休息后希望室友使用耳机", importance: "MUST", category: "作息声音" },
  { text: "需要午休", importance: "PREFER", category: "作息声音" },
  { text: "对灯光比较敏感", importance: "PREFER", category: "寝室环境" },
  { text: "希望公共区域保持整洁", importance: "MUST", category: "卫生整洁" },
  { text: "愿意参加寝室轮值", importance: "NEGOTIABLE", category: "卫生整洁" },
  { text: "希望偶尔一起学习", importance: "REFERENCE", category: "共同活动" },
  { text: "希望周末偶尔一起运动", importance: "REFERENCE", category: "共同活动" },
];

const INITIAL_ROWS: PreferenceRow[] = [
  { id: "pref-smoking", text: "不接受室友在寝室内吸烟", importance: "DEAL_BREAKER", source: "QUICK" },
  { id: "pref-audio", text: "可以接受室友晚睡，但晚上休息后需要使用耳机", importance: "NEGOTIABLE", source: "CUSTOM" },
];

const MATCHED_MEMBERS = [
  { avatar: "A", name: "Alice Chen", trait: "早睡 · 喜欢安静", reason: "本人" },
  { avatar: "陈", name: "陈同学", trait: "正常作息 · 不在寝室吸烟", reason: "硬性条件相容" },
  { avatar: "林", name: "林同学", trait: "晚睡 · 接受使用耳机", reason: "愿意尊重声音边界" },
  { avatar: "周", name: "周同学", trait: "需要午休 · 对灯光敏感", reason: "环境需求相近" },
];

const NEGOTIATION_STAGES = [
  { title: "检查硬性条件", text: "排除存在室内吸烟等不可接受条件的候选，不向其他成员公开原始原因。" },
  { title: "候选 Agent 交换最小必要表达", text: "只讨论已经由本人确认、且与共同生活直接相关的需求。" },
  { title: "协调可以谈判的差异", text: "围绕晚睡、耳机、灯光与公共区域规则形成可执行承诺。" },
  { title: "生成可供本人确认的室友组合", text: "整理推荐理由、共同基础与仍需入住后确认的事项。" },
];
const REQUIRED_TASK_STORAGE_KEY = "campusagent:dorm-required-task";

function importanceLabel(value: Importance) {
  return IMPORTANCE_OPTIONS.find((item) => item.value === value)?.label ?? value;
}

function interpretPreference(text: string, importance: Importance) {
  if (/不.*抽烟|不.*吸烟|烟味/.test(text)) return "硬性排除在寝室内吸烟的候选室友";
  if (/耳机|外放|声音|安静/.test(text)) return importance === "NEGOTIABLE" ? "可以接受作息差异，但夜间声音边界需要协商确认" : "夜间不得外放声音，优先寻找愿意使用耳机的室友";
  if (/午休/.test(text)) return "优先寻找能够尊重午休时间的室友";
  if (/灯光|开灯/.test(text)) return "匹配时关注夜间灯光使用方式";
  if (/整洁|卫生|垃圾/.test(text)) return "匹配时关注公共区域卫生习惯";
  if (/轮值|值日|打扫/.test(text)) return "愿意就公共区域清洁方式进行协商";
  if (/学习/.test(text)) return "把共同学习意愿作为弱偏好，不作为排除条件";
  if (/运动|活动/.test(text)) return "把共同活动意愿作为相处参考";
  return importance === "DEAL_BREAKER" ? `作为硬性排除条件：${text}` : `在候选协商中表达：${text}`;
}

function phaseIndex(phase: DemoPhase, approved: boolean) {
  if (approved) return 5;
  if (phase === "intro" || phase === "preferences") return 0;
  if (phase === "intent") return 1;
  if (phase === "waiting") return 2;
  if (phase === "negotiation" || phase === "counter_proposal" || phase === "no_consensus" || phase === "withdrawn") return 3;
  if (phase === "proposal") return 4;
  return 5;
}

function PreferenceRowsEditor({ rows, setRows, compact = false }: { rows: PreferenceRow[]; setRows: Dispatch<SetStateAction<PreferenceRow[]>>; compact?: boolean }) {
  const addBlank = () => {
    if (rows.length >= 10) return;
    setRows((current) => [...current, { id: `pref-${Date.now()}`, text: "", importance: "PREFER", source: "CUSTOM" }]);
  };
  const addQuick = (item: (typeof QUICK_ITEMS)[number]) => {
    if (rows.length >= 10 || rows.some((row) => row.text === item.text)) return;
    setRows((current) => [...current, { id: `pref-${Date.now()}-${current.length}`, text: item.text, importance: item.importance, source: "QUICK" }]);
  };
  const updateRow = (id: string, patch: Partial<PreferenceRow>) => setRows((current) => current.map((row) => row.id === id ? { ...row, ...patch } : row));
  const removeRow = (id: string) => setRows((current) => current.filter((row) => row.id !== id));

  return <section className={`dorm-preference-editor${compact ? " is-compact" : ""}`}>
    <header><div><span>{compact ? "补充需求" : "05 · 逐条补充偏好"}</span><h3>{compact ? "补充这版方案没有满足的需求" : "每一栏只表达一件事情"}</h3><p>每条偏好独立设置重要程度，Agent 会逐条识别，不会遗漏“不抽烟”等硬性条件。</p></div><em>{rows.length}/10 条</em></header>
    <div className="dorm-quick-preferences"><span>快速补充</span>{QUICK_ITEMS.map((item) => <button key={item.text} type="button" disabled={rows.some((row) => row.text === item.text) || rows.length >= 10} onClick={() => addQuick(item)}>＋ {item.text}<small>{importanceLabel(item.importance)}</small></button>)}</div>
    <div className="dorm-preference-rows">{rows.map((row, index) => <article key={row.id}>
      <span>{String(index + 1).padStart(2, "0")}</span>
      <label><small>偏好内容</small><input aria-label={`偏好内容 ${index + 1}`} value={row.text} onChange={(event) => updateRow(row.id, { text: event.target.value, source: "CUSTOM" })} placeholder="用一句话描述一项室友或共同生活需求" maxLength={100} /></label>
      <label><small>重要程度</small><select aria-label={`重要程度 ${index + 1}`} value={row.importance} onChange={(event) => updateRow(row.id, { importance: event.target.value as Importance })}>{IMPORTANCE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
      <button type="button" onClick={() => removeRow(row.id)} aria-label={`删除偏好 ${index + 1}`}>×</button>
    </article>)}</div>
    <button className="dorm-add-preference" type="button" onClick={addBlank} disabled={rows.length >= 10}>＋ 添加一条偏好</button>
  </section>;
}

function DormitoryMatchDemo() {
  const [phase, setPhase] = useState<DemoPhase>("intro");
  const [preferences, setPreferences] = useState<Record<PreferenceKey, string>>({ schedule: "早睡型", environment: "喜欢安静", communication: "先由 Agent 协调", social: "偶尔参与" });
  const [priorities, setPriorities] = useState<Record<PreferenceKey, Importance>>({ schedule: "PREFER", environment: "MUST", communication: "NEGOTIABLE", social: "REFERENCE" });
  const [customRows, setCustomRows] = useState<PreferenceRow[]>(INITIAL_ROWS);
  const [supplementRows, setSupplementRows] = useState<PreferenceRow[]>([]);
  const [consent, setConsent] = useState(true);
  const [intentAnalyzing, setIntentAnalyzing] = useState(false);
  const [joinedCount, setJoinedCount] = useState(1);
  const [negotiationAttempt, setNegotiationAttempt] = useState(1);
  const [negotiationStage, setNegotiationStage] = useState(0);
  const [counterProposalAcceptedAttempt, setCounterProposalAcceptedAttempt] = useState<number | null>(null);
  const [supplementing, setSupplementing] = useState(false);
  const [supplementReview, setSupplementReview] = useState(false);
  const [approved, setApproved] = useState(false);

  const current = phaseIndex(phase, approved);
  const validCustomRows = useMemo(() => customRows.filter((row) => row.text.trim()), [customRows]);
  const validSupplementRows = useMemo(() => supplementRows.filter((row) => row.text.trim()), [supplementRows]);
  const hasInvalidCustomRows = customRows.some((row) => !row.text.trim());
  const hasInvalidSupplementRows = supplementRows.some((row) => !row.text.trim());
  const intentPoints = useMemo<IntentPoint[]>(() => {
    const structured = PREFERENCE_GROUPS.map((group) => ({ id: `structured-${group.key}`, original: preferences[group.key], interpretation: group.key === "schedule" ? `作息偏好为“${preferences[group.key]}”，用于寻找作息相容或愿意协调的候选` : group.key === "environment" ? `优先寻找接受“${preferences[group.key]}”环境的候选` : group.key === "communication" ? `发生分歧时倾向“${preferences[group.key]}”` : `相处期待为“${preferences[group.key]}”`, importance: priorities[group.key], source: `选择项 · ${group.title}` }));
    const custom = validCustomRows.map((row) => ({ id: row.id, original: row.text, interpretation: interpretPreference(row.text, row.importance), importance: row.importance, source: row.source === "QUICK" ? "快速补充" : "自定义偏好" }));
    return [...structured, ...custom];
  }, [preferences, priorities, validCustomRows]);
  const hardConstraintCount = intentPoints.filter((point) => point.importance === "DEAL_BREAKER" || point.importance === "MUST").length;
  const agreements = useMemo(() => {
    const base = ["寝室内不吸烟", "晚上休息后音视频使用耳机", "每周共同确认公共区域清洁安排", "晚睡成员使用独立灯光", "午休时提前沟通通话需求"];
    return counterProposalAcceptedAttempt === negotiationAttempt ? [...base, "23:30 后关闭主灯，临时开灯提前说明"] : base;
  }, [counterProposalAcceptedAttempt, negotiationAttempt]);

  useEffect(() => {
    const status = approved ? "COMPLETED" : phase === "intent" ? "WAITING_INTENT_CONFIRM" : phase === "waiting" ? "WAITING_MATCH" : phase === "negotiation" ? "NEGOTIATING" : phase === "counter_proposal" ? "ACTION_REQUIRED" : phase === "proposal" ? "CONFIRMING" : phase === "withdrawn" || phase === "no_consensus" ? "REMATCH_REQUIRED" : phase === "confirmed" ? "SCHOOL_REVIEW" : "WAITING_INPUT";
    window.localStorage.setItem(REQUIRED_TASK_STORAGE_KEY, JSON.stringify({ status, updated_at: new Date().toISOString() }));
  }, [approved, phase]);

  useEffect(() => {
    if (phase !== "waiting") return;
    setJoinedCount(1);
    const timers = [
      window.setTimeout(() => setJoinedCount(2), 1200),
      window.setTimeout(() => setJoinedCount(3), 2400),
      window.setTimeout(() => setJoinedCount(4), 3600),
      window.setTimeout(() => { setNegotiationStage(0); setPhase("negotiation"); }, 4800),
    ];
    return () => timers.forEach(window.clearTimeout);
  }, [phase]);

  useEffect(() => {
    if (phase !== "negotiation") return;
    const hasAcceptedCounterProposal = counterProposalAcceptedAttempt === negotiationAttempt;
    setNegotiationStage(hasAcceptedCounterProposal ? 2 : 0);
    const timers = hasAcceptedCounterProposal
      ? [
          window.setTimeout(() => setNegotiationStage(3), 1100),
          window.setTimeout(() => setNegotiationStage(4), 2200),
          window.setTimeout(() => setPhase("proposal"), 3300),
        ]
      : [
          window.setTimeout(() => setNegotiationStage(1), 1100),
          window.setTimeout(() => setNegotiationStage(2), 2200),
          window.setTimeout(() => setPhase("counter_proposal"), 3300),
        ];
    return () => timers.forEach(window.clearTimeout);
  }, [phase, negotiationAttempt, counterProposalAcceptedAttempt]);

  const startIntentAnalysis = () => {
    if (!validCustomRows.length || hasInvalidCustomRows) return;
    setIntentAnalyzing(true);
    window.setTimeout(() => { setIntentAnalyzing(false); setPhase("intent"); }, 900);
  };

  const confirmSupplement = () => {
    if (negotiationAttempt >= 3 || !validSupplementRows.length) return;
    setCustomRows((current) => [...current, ...validSupplementRows.map((row) => ({ ...row, id: `confirmed-${Date.now()}-${row.id}` }))].slice(0, 10));
    setNegotiationAttempt((attempt) => attempt + 1);
    setCounterProposalAcceptedAttempt(null);
    setSupplementRows([]);
    setSupplementing(false);
    setSupplementReview(false);
    setPhase("negotiation");
  };

  const restartMatch = () => {
    setNegotiationAttempt(1);
    setCounterProposalAcceptedAttempt(null);
    setSupplementRows([]);
    setSupplementing(false);
    setSupplementReview(false);
    setPhase("waiting");
  };

  const resetDemo = () => {
    setPhase("intro");
    setApproved(false);
    setNegotiationAttempt(1);
    setCounterProposalAcceptedAttempt(null);
    setSupplementRows([]);
    setSupplementing(false);
    setSupplementReview(false);
  };

  const participantStates = [
    { avatar: "A", name: "Alice Chen", readyAt: 1 },
    { avatar: "陈", name: "陈同学", readyAt: 2 },
    { avatar: "林", name: "林同学", readyAt: 3 },
    { avatar: "周", name: "周同学", readyAt: 4 },
  ];

  return <section className="dorm-match-demo" aria-label="新生宿舍共识安排演示">
    <header className="dorm-match-header"><Link href="/scenes" aria-label="返回协作空间">←</Link><div><span>信息科学技术学院 · 2026级新生</span><h1>新生宿舍共识安排</h1><small>表达需求 · 等待成员自主参加 · Agent 自动谈判 · 本人确认结果</small></div><div className="dorm-match-header-meta"><span><small>当前进度</small><strong>{current + 1}/6</strong></span><span><small>谈判次数</small><strong>{negotiationAttempt}/3</strong></span><em>演示模式</em></div></header>

    <div className="dorm-match-layout">
      <aside className="dorm-match-steps" aria-label="协作进度"><header><strong>室友匹配进度</strong><small>等待与谈判自动进行</small></header><ol>{PHASES.map((item, index) => <li key={item.title} className={index < current ? "is-done" : index === current ? "is-current" : ""}><span>{index < current ? "✓" : index + 1}</span><div><strong>{item.title}</strong><small>{index < current ? "已完成" : item.note}</small></div></li>)}</ol><section className="dorm-match-owner"><span>固定规则</span><strong>一个匹配会话最多谈判 3 次</strong><p>三次仍未形成所有成员都接受的组合，就结束本轮并重新匹配候选人。</p></section></aside>

      <main className="dorm-match-main">
        {phase === "intro" && <div className="dorm-match-intro"><div className="dorm-match-kicker"><span>友</span><p>先找到更合适的室友<br />再一起谈出舒服的相处方式</p></div><h2>让你的 Agent 帮你寻找室友</h2><p className="dorm-match-lead">你只需要表达需求、确认 Agent 理解并决定是否接受结果。其他同学自主加入后，多个 Agent 会自动协商；如果结果不满意，你可以补充需求，最多重新谈判两次。</p><div className="dorm-match-principles"><article><span>01</span><strong>偏好逐条表达</strong><p>一栏只填写一件事情，并分别设置重要程度，确保“不抽烟”等硬性需求不会遗漏。</p></article><article><span>02</span><strong>等待和谈判自动进行</strong><p>提交后可以离开页面，成员到齐后系统自动开始，完成时通过校园消息提醒。</p></article><article><span>03</span><strong>结果不满意可以补充</strong><p>补充需求再次经过意图确认；一轮匹配最多进行三次 Agent 谈判。</p></article></div><aside className="dorm-match-scope"><span>隐私范围</span><div><strong>心理健康信息、私人对话和性格评价不参与匹配</strong><p>学校只能看到最终确认结果和必要住宿条件，不能查看学生的原始私人表达。</p></div></aside></div>}

        {phase === "preferences" && <div className="dorm-match-form"><header><span>步骤 1 · 表达需求</span><h2>你希望和怎样的室友一起生活？</h2><p>先完成四项基础选择，再逐条补充没有覆盖的需求。每条偏好都必须设置重要程度。</p></header><div className="dorm-match-question-list">{PREFERENCE_GROUPS.map((group) => <section key={group.key}><header><span>{group.index}</span><div><h3>{group.title}</h3><p>{group.description}</p></div><label><span>重要程度</span><select value={priorities[group.key]} onChange={(event) => setPriorities((value) => ({ ...value, [group.key]: event.target.value as Importance }))}>{IMPORTANCE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label></header><div>{group.options.map((option) => <button key={option} type="button" className={preferences[group.key] === option ? "is-selected" : ""} onClick={() => setPreferences((value) => ({ ...value, [group.key]: option }))}><span>{preferences[group.key] === option ? "✓" : ""}</span>{option}</button>)}</div></section>)}</div><PreferenceRowsEditor rows={customRows} setRows={setCustomRows} /><label className="dorm-match-consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span><strong>仅授权本次室友匹配使用以上表达</strong><small>Agent 必须先逐条展示识别结果；本人确认前不得参与协商。</small></span></label></div>}

        {phase === "intent" && <div className="dorm-intent-review"><header><span>步骤 2 · 确认意图</span><h2>Agent 共识别出 {intentPoints.length} 个需求点</h2><p>结构化选项直接映射，自定义内容逐条进行语义识别。请确认 Agent 将如何代表你。</p></header><section className="dorm-intent-overview"><div><span>CA</span><p><small>识别完成</small><strong>{intentPoints.length} 个需求点 · {hardConstraintCount} 个硬性条件</strong></p></div><button type="button" onClick={() => setPhase("preferences")}>返回修改</button></section><div className="dorm-intent-points">{intentPoints.map((point, index) => <article key={point.id}><span>{String(index + 1).padStart(2, "0")}</span><div><header><strong>{point.original}</strong><em className={`is-${point.importance.toLowerCase()}`}>{importanceLabel(point.importance)}</em></header><p><b>Agent 理解</b>{point.interpretation}</p><small>来源：{point.source}</small></div><i>✓</i></article>)}</div><aside className="dorm-intent-confirm"><span>!</span><div><strong>确认的是“Agent 如何代表你”，不是同意最终分配</strong><p>硬性条件不会被 Agent 擅自让步；最终室友组合仍会再次交给所有成员确认。</p></div></aside></div>}

        {phase === "waiting" && <div className="dorm-waiting-room"><header><span>步骤 3 · 等待成员</span><h2>正在等待候选同学自主加入</h2><p>成员到齐并完成意图确认后，系统会自动开始第 {negotiationAttempt}/3 次谈判。你可以离开页面，完成后会收到通知。</p></header><section className="dorm-waiting-progress"><div><span>{joinedCount}/4</span><p><strong>{joinedCount === 4 ? "成员已到齐" : "等待成员加入"}</strong><small>{joinedCount === 4 ? "正在准备自动谈判…" : "只显示参与状态，不公开任何偏好"}</small></p></div><div className="dorm-waiting-bar"><i style={{ width: `${joinedCount * 25}%` }} /></div></section><div className="dorm-waiting-members">{participantStates.map((member) => { const ready = joinedCount >= member.readyAt; return <article key={member.name} className={ready ? "is-ready" : ""}><span>{member.avatar}</span><div><strong>{member.name}</strong><small>{ready ? "已加入 · 意图已确认" : "等待本人回应邀请"}</small></div><i>{ready ? "✓ 已准备" : "等待中"}</i></article>; })}</div><aside className="dorm-auto-notice"><span>铃</span><div><strong>不需要停留在这个页面</strong><p>其他成员准备完成后，Agent 谈判会自动启动；结果生成时发送校园通知。</p></div><button type="button">完成后通知我</button></aside></div>}

        {phase === "negotiation" && <div className="dorm-match-negotiation"><header><span>步骤 4 · 第 {negotiationAttempt}/3 次自动谈判</span><h2>多个 Agent 正在寻找共同接受的室友组合</h2><p>系统会自动完成本次谈判，不需要手动点击下一轮。只展示公开摘要，不展示任何成员的原始偏好。</p></header><section className="dorm-negotiation-attempts">{[1,2,3].map((attempt) => <div key={attempt} className={attempt < negotiationAttempt ? "is-done" : attempt === negotiationAttempt ? "is-current" : ""}><span>{attempt < negotiationAttempt ? "✓" : attempt}</span><p><strong>第 {attempt} 次谈判</strong><small>{attempt < negotiationAttempt ? "已完成并补充需求" : attempt === negotiationAttempt ? "自动进行中" : "尚未使用"}</small></p></div>)}</section><section className="dorm-negotiation-stage"><header><div><span className="is-live" />{negotiationStage < NEGOTIATION_STAGES.length ? NEGOTIATION_STAGES[negotiationStage]?.title ?? "正在初始化安全协商" : "正在生成结果"}</div><small>完成后自动进入确认页面</small></header><div className="dorm-auto-negotiation-log">{NEGOTIATION_STAGES.map((stage, index) => <article key={stage.title} className={index < negotiationStage ? "is-done" : index === negotiationStage ? "is-current" : ""}><span>{index < negotiationStage ? "✓" : index + 1}</span><div><strong>{stage.title}</strong><p>{stage.text}</p></div><i>{index < negotiationStage ? "已完成" : index === negotiationStage ? "处理中…" : "等待"}</i></article>)}</div></section><aside className="dorm-negotiation-boundary"><span>CA</span><div><strong>Agent 只在你确认的边界内谈判</strong><p>“不接受室内吸烟”等硬性条件只用于排除候选，不会进入折中谈判，也不会向候选说明个人原因。</p></div></aside></div>}

        {phase === "counter_proposal" && <div className="dorm-counter-proposal"><header><span>谈判已暂停 · 需要本人决定</span><h2>其他成员提出了一项补充条件</h2><p>这项条件会影响共同生活规则，你的 Agent 无权默认接受。请先查看变化，再决定是否继续参加本轮匹配。</p></header><section className="dorm-counter-proposal-card"><div className="dorm-counter-source"><span>林</span><div><small>林同学的 Agent</small><strong>希望补充夜间作息约定</strong></div><em>新增条件</em></div><blockquote>“可以接受晚睡成员，但晚上 23:30 后应关闭主灯；临时需要开灯时使用独立灯光，并提前在寝室群说明。”</blockquote><dl><div><dt>对你的影响</dt><dd>需要接受 23:30 后关闭寝室主灯</dd></div><div><dt>你的硬性条件</dt><dd>不抽烟、夜间声音边界均未改变</dd></div><div><dt>当前状态</dt><dd>等待你的明确选择，谈判已暂停</dd></div></dl></section><aside><span>!</span><div><strong>你始终拥有退出权</strong><p>选择退出后，你的偏好不会继续参与本轮谈判；其他成员可以继续协作，你也可以保留需求重新寻找候选室友。</p></div></aside></div>}

        {phase === "proposal" && <div className="dorm-match-proposal"><header><span>步骤 5 · 第 {negotiationAttempt}/3 次谈判结果</span><h2>推荐室友组合 A</h2><p>所有候选都满足“不在寝室内吸烟”等硬性条件，并对存在差异的生活习惯形成了明确承诺。</p></header><section className="dorm-proposal-summary"><div><span>友</span><div><small>Agent 推荐组合</small><strong>Alice、陈同学、林同学、周同学</strong><p>不是性格评分 · 基于确认需求、硬性筛选和协商承诺</p></div></div><dl><div><dt>硬性条件</dt><dd>{hardConstraintCount} 项满足</dd></div><div><dt>共同基础</dt><dd>{agreements.length} 项</dd></div><div><dt>谈判次数</dt><dd>{negotiationAttempt}/3</dd></div></dl></section><section className="dorm-proposal-members"><header><strong>为什么建议这三位室友</strong><small>只展示候选本人允许公开的生活信息</small></header><div>{MATCHED_MEMBERS.map((member, index) => <article key={member.name}><span>{member.avatar}</span><div><strong>{member.name}{index === 0 && <em>我</em>}</strong><small>{member.trait} · {member.reason}</small></div><i className={index < 3 ? "is-confirmed" : ""}>{index < 3 ? "✓ 已确认" : "等待你的确认"}</i></article>)}</div></section><div className="dorm-proposal-columns"><section><header><span>✓</span><div><strong>Agent 谈出的共同生活基础</strong><small>所有成员接受后生效</small></div></header><ul>{agreements.map((item) => <li key={item}><span>✓</span>{item}</li>)}</ul></section><section><header><span>!</span><div><strong>入住后继续确认</strong><small>不影响室友选择</small></div></header><ul><li><span>1</span>空调温度由入住后共同决定</li><li><span>2</span>周末访客提前在寝室群沟通</li></ul></section></div>
          {supplementing && <section className="dorm-supplement-panel"><header><div><span>补充需求 · 将开启第 {Math.min(3, negotiationAttempt + 1)}/3 次谈判</span><strong>{supplementReview ? "确认 Agent 对新增需求的理解" : "告诉 Agent 这版结果还缺少什么"}</strong></div><button type="button" onClick={() => { setSupplementing(false); setSupplementReview(false); }}>×</button></header>{!supplementReview ? <PreferenceRowsEditor rows={supplementRows} setRows={setSupplementRows} compact /> : <div className="dorm-supplement-review">{validSupplementRows.map((row, index) => <article key={row.id}><span>{index + 1}</span><div><strong>{row.text}</strong><p>{interpretPreference(row.text, row.importance)}</p><small>{importanceLabel(row.importance)} · 新增需求</small></div><i>✓</i></article>)}</div>}<footer><p>{supplementReview ? "确认后系统自动重新谈判，你可以离开页面等待通知。" : "新增内容不会直接修改结果，必须先确认意图再交给其他 Agent。"}</p>{!supplementReview ? <button type="button" disabled={!validSupplementRows.length || hasInvalidSupplementRows} onClick={() => setSupplementReview(true)}>让 Agent 识别补充需求</button> : <button type="button" onClick={confirmSupplement}>确认并自动重新谈判</button>}</footer></section>}
        </div>}

        {phase === "no_consensus" && <div className="dorm-no-consensus"><span>↻</span><small>本轮谈判已结束</small><h2>暂未找到所有成员都能接受的方案</h2><p>本轮已经完成 3 次谈判，仍有成员不接受最终组合。系统不会继续强行协调，也不会用多数票决定室友关系。</p><section><article><strong>保留已确认需求</strong><p>重新匹配时可以沿用“不接受室内吸烟”等已经确认的偏好。</p></article><article><strong>更换候选室友</strong><p>创建新的匹配会话，从其他符合硬性条件的候选中重新寻找。</p></article><article><strong>重新获得本人确认</strong><p>新组合生成后仍需所有成员分别确认。</p></article></section></div>}

        {phase === "withdrawn" && <div className="dorm-no-consensus dorm-withdrawn"><span>✓</span><small>已按你的选择退出</small><h2>你已退出本轮室友匹配</h2><p>你的 Agent 已停止代表你参与谈判，也不会接受其他成员新增的共同生活条件。退出不影响其他同学继续协作。</p><section><article><strong>偏好仍由你保管</strong><p>已经确认的个人需求会保留在本次演示中，不会转交给新的候选人。</p></article><article><strong>本轮不再代表你</strong><p>其他 Agent 不会再收到你的表达，也不能把你加入最终室友组合。</p></article><article><strong>可以重新寻找</strong><p>需要时可以保留现有需求，重新匹配一组新的候选室友。</p></article></section></div>}

        {phase === "confirmed" && <div className="dorm-match-proposal"><header><span>步骤 6 · 学校审核</span><h2>{approved ? "正式宿舍安排已确认" : "四位同学已互相确认"}</h2><p>{approved ? "学校住宿工作组已完成审核并分配东九 T207，寝室协作群已经建立。" : "室友组合已经获得所有成员确认，下一步由学校责任人审核必要住宿条件并安排具体寝室。"}</p></header><section className="dorm-proposal-summary"><div><span>{approved ? "✓" : "审"}</span><div><small>{approved ? "正式安排" : "等待责任人审核"}</small><strong>{approved ? "东九学生公寓 T207" : "Alice、陈同学、林同学、周同学"}</strong><p>{approved ? "安排编号 JNU-DORM-2026-0207" : "学校不能查看原始偏好与私人 Agent 数据"}</p></div></div><dl><div><dt>成员确认</dt><dd>4/4</dd></div><div><dt>谈判次数</dt><dd>{negotiationAttempt}/3</dd></div><div><dt>审核状态</dt><dd>{approved ? "已完成" : "待审核"}</dd></div></dl></section><aside className={`dorm-review-state${approved ? " is-approved" : ""}`}><span>{approved ? "✓" : "审"}</span><div><strong>{approved ? "学校审核已完成" : "重要决定仍由责任人确认"}</strong><p>{approved ? "寝室协作群已创建；后续调整仍需本人申请并由相应责任人处理。" : "住宿工作组只查看最终组合、必要住宿条件和审计记录，不读取任何人的私人思想。"}</p></div></aside></div>}
      </main>

      <aside className="dorm-match-context"><section><header><span>我的参与</span><strong>{phase === "waiting" ? `${joinedCount}/4 已准备` : phase === "negotiation" ? `自动谈判 ${negotiationAttempt}/3` : phase === "counter_proposal" ? "谈判暂停 · 待决定" : phase === "withdrawn" ? "已退出本轮" : phase === "proposal" ? "等待本人决定" : phase === "intent" ? "待确认意图" : "自主参与"}</strong></header><div className="dorm-context-progress"><i style={{ width: `${Math.max(8, (current / 5) * 100)}%` }} /></div><dl><div><dt>本次目标</dt><dd>寻找合适室友</dd></div><div><dt>原始表达</dt><dd>仅本人可见</dd></div><div><dt>硬性条件</dt><dd>不可被 Agent 让步</dd></div><div><dt>最终组合</dt><dd>所有成员确认</dd></div></dl></section><section className="dorm-context-agent"><header><span>CA</span><div><small>我的个人 Agent</small><strong>代表表达，不替我选择</strong></div></header><p>{phase === "waiting" ? "你可以离开页面，我会在其他成员准备完成后自动开始。" : phase === "negotiation" ? "正在自动协商；遇到别人新增条件时，我会暂停并请你决定。" : phase === "counter_proposal" ? "谈判已经暂停；未经你明确接受，我不会继续参加。" : phase === "withdrawn" ? "我已停止代表你参与本轮谈判。" : phase === "proposal" ? "如果结果不满意，可以逐条补充需求后重新谈判。" : "我会逐条理解你的需求，并在行动前请你确认。"}</p></section><section className="dorm-context-privacy"><span>协商边界</span><strong>敏感数据严格分域</strong><ul><li>不读取私人 Agent 对话</li><li>不使用心理健康信息</li><li>不生成性格评价或排名</li><li>硬性条件不进入折中谈判</li></ul><button type="button">查看本次授权范围</button></section><section className="dorm-context-help"><span>不想继续自动匹配？</span><strong>随时可以转人工</strong><p>特殊住宿需求无需向候选同学公开，可单独联系学院住宿工作组。</p><button type="button">申请人工协助</button></section></aside>
    </div>

    <footer className="dorm-match-actions"><p><span>i</span>{phase === "intro" ? "这是交互式演示，不会提交真实住宿申请。" : phase === "preferences" ? "每条偏好都需要内容和重要程度。" : phase === "intent" ? "确认理解准确后，Agent 才能代表你。" : phase === "waiting" ? "等待成员时可以离开页面，完成后会收到通知。" : phase === "negotiation" ? "Agent 正在自动谈判；发现新增条件时会暂停。" : phase === "counter_proposal" ? "未经本人明确接受，Agent 不会继续谈判。" : phase === "proposal" ? negotiationAttempt < 3 ? "可以接受结果，或补充需求后自动重新谈判。" : "已经达到 3 次上限：接受结果或结束本轮。" : phase === "no_consensus" ? "重新开启后会创建新的匹配会话。" : phase === "withdrawn" ? "你可以离开，也可以重新寻找其他候选。" : approved ? "演示已经完成。" : "所有成员已确认，等待学校审核。"}</p><div>
      {phase === "intro" && <button className="is-primary" type="button" onClick={() => setPhase("preferences")}>开始表达室友需求 <span>→</span></button>}
      {phase === "preferences" && <button className="is-primary" type="button" disabled={!consent || !validCustomRows.length || hasInvalidCustomRows || intentAnalyzing} onClick={startIntentAnalysis}>{intentAnalyzing ? "Agent 正在逐条识别…" : "让 Agent 识别全部需求"}<span>→</span></button>}
      {phase === "intent" && <><button type="button" onClick={() => setPhase("preferences")}>返回修改</button><button className="is-primary" type="button" onClick={() => setPhase("waiting")}>确认意图并参加匹配 <span>→</span></button></>}
      {phase === "waiting" && <button type="button" onClick={() => setPhase("preferences")}>撤回本次参与</button>}
      {phase === "negotiation" && <button type="button" disabled>Agent 自动谈判中…</button>}
      {phase === "counter_proposal" && <><button className="is-danger" type="button" onClick={() => setPhase("withdrawn")}>不同意，退出本轮</button><button className="is-primary" type="button" onClick={() => { setCounterProposalAcceptedAttempt(negotiationAttempt); setPhase("negotiation"); }}>接受条件，继续谈判 <span>→</span></button></>}
      {phase === "proposal" && !supplementing && <>{negotiationAttempt < 3 ? <button type="button" onClick={() => { setSupplementRows([]); setSupplementReview(false); setSupplementing(true); }}>补充我的需求</button> : <button type="button" onClick={() => setPhase("no_consensus")}>本轮仍不合适</button>}<button className="is-primary" type="button" onClick={() => setPhase("confirmed")}>接受这组室友 <span>→</span></button></>}
      {phase === "no_consensus" && <><button type="button" onClick={() => setPhase("preferences")}>调整需求</button><button className="is-primary" type="button" onClick={restartMatch}>保留需求，重新开启匹配 <span>→</span></button></>}
      {phase === "withdrawn" && <><Link className="dorm-action-link" href="/scenes">返回协作空间</Link><button className="is-primary" type="button" onClick={restartMatch}>保留需求，匹配其他候选 <span>→</span></button></>}
      {phase === "confirmed" && !approved && <button className="is-primary" type="button" onClick={() => setApproved(true)}>模拟学校审核 <span>→</span></button>}
      {approved && <button type="button" onClick={resetDemo}>重新体验演示</button>}
    </div></footer>
  </section>;
}

export default function DormitoryMatchPage() {
  return <AppShell requireAuth><DormitoryMatchDemo /></AppShell>;
}
