"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app/AppShell";

type TaskStatus = "DRAFT" | "NEEDS_CONFIRMATION" | "RUNNING" | "WAITING" | "SCHEDULED" | "COMPLETED" | "CANCELLED";

interface AgentTask {
  id: string;
  title: string;
  description: string;
  category: string;
  status: TaskStatus;
  statusLabel: string;
  updatedAt: string;
  owner: string;
  receipt?: string;
  timeline: Array<{ time: string; title: string; detail: string; done: boolean }>;
  dataUsed: string[];
  dataExcluded: string[];
}

const QUICK_TASKS = [
  { id: "schedule", icon: "课", type: "查询", title: "查询课程", detail: "课表、考试与地点", targetTask: "schedule" },
  { id: "digest", icon: "知", type: "委托", title: "通知摘要", detail: "整理学院与班级重点", targetTask: "digest" },
  { id: "leave", icon: "假", type: "办理", title: "请假申请", detail: "准备理由与课程信息", targetTask: "leave" },
  { id: "certificate", icon: "证", type: "办理", title: "在读证明", detail: "生成申请草稿", targetTask: "certificate" },
  { id: "venue", icon: "场", type: "办理", title: "场地预约", detail: "筛选可用教室与场馆", targetTask: "venue" },
  { id: "repair", icon: "修", type: "办理", title: "宿舍报修", detail: "记录问题与上门时间", targetTask: "repair" },
];

const CREATE_TEMPLATE_DETAILS: Record<string, { goal: string; category: string; owner: string; dataUsed: string[] }> = {
  schedule: { goal: "查询并整理我的课程、考试时间和上课地点。", category: "课程查询", owner: "个人 Agent", dataUsed: ["个人课表", "考试安排", "校区信息"] },
  digest: { goal: "整理学院、班级和个人通知，生成一份重点摘要。", category: "消息整理", owner: "个人 Agent", dataUsed: ["校园通知", "班级消息", "个人待办"] },
  leave: { goal: "准备课程请假申请草稿，并在提交前让我最终确认。", category: "学生事务", owner: "学生工作办公室", dataUsed: ["姓名", "学号", "课程安排"] },
  certificate: { goal: "核对学籍信息并生成在读证明申请草稿。", category: "证明申请", owner: "教务处", dataUsed: ["姓名", "学号", "学院", "在读状态"] },
  venue: { goal: "筛选符合时间和人数要求的可预约校园场地。", category: "场地预约", owner: "校园场地服务", dataUsed: ["预约时段", "参与人数", "校区"] },
  repair: { goal: "创建宿舍报修任务，整理问题描述和可上门时间。", category: "宿舍服务", owner: "后勤服务中心", dataUsed: ["宿舍楼栋", "房间号", "联系电话"] },
};

const INITIAL_TASKS: AgentTask[] = [
  {
    id: "certificate",
    title: "申请在读证明",
    description: "已根据学籍信息生成申请草稿，正在等待你确认用途和接收方式。",
    category: "证明申请",
    status: "NEEDS_CONFIRMATION",
    statusLabel: "需要确认",
    updatedAt: "10:23",
    owner: "教务处",
    timeline: [
      { time: "10:20", title: "任务已创建", detail: "你从快捷任务发起了在读证明申请", done: true },
      { time: "10:21", title: "已读取必要信息", detail: "读取姓名、学号、学院和在读状态", done: true },
      { time: "10:22", title: "已生成申请草稿", detail: "用途：实习材料；接收方式：电子版", done: true },
      { time: "10:23", title: "等待你的确认", detail: "确认后才会进入模拟提交步骤", done: false },
      { time: "—", title: "尚未提交", detail: "Agent 不会代替你做最终决定", done: false },
    ],
    dataUsed: ["姓名", "学号", "学院", "在读状态"],
    dataExcluded: ["个人对话", "个人知识库", "心理健康信息"],
  },
  {
    id: "leave",
    title: "课程请假申请",
    description: "申请草稿已准备，缺少请假时间与课程范围确认。",
    category: "学生事务",
    status: "NEEDS_CONFIRMATION",
    statusLabel: "需要确认",
    updatedAt: "09:46",
    owner: "学生工作办公室",
    timeline: [
      { time: "09:42", title: "任务已创建", detail: "已选择课程请假场景", done: true },
      { time: "09:44", title: "已整理课程", detail: "发现请假时段涉及 2 门课程", done: true },
      { time: "09:46", title: "等待补充", detail: "请确认请假原因和起止时间", done: true },
      { time: "—", title: "尚未提交", detail: "补充并确认后才继续", done: false },
    ],
    dataUsed: ["姓名", "学号", "课程安排"],
    dataExcluded: ["个人对话", "个人知识库", "心理健康信息"],
  },
  {
    id: "digest",
    title: "生成每日校园简报",
    description: "正在整理学院通知、班级消息和个人截止事项。",
    category: "消息整理",
    status: "RUNNING",
    statusLabel: "正在执行",
    updatedAt: "刚刚",
    owner: "个人 Agent",
    timeline: [
      { time: "10:28", title: "定时任务触发", detail: "开始生成今天的校园简报", done: true },
      { time: "10:29", title: "正在整理消息", detail: "按重要程度与截止时间去重排序", done: true },
      { time: "—", title: "等待生成结果", detail: "完成后会出现在消息与通知中", done: false },
    ],
    dataUsed: ["校园通知", "班级消息", "个人待办"],
    dataExcluded: ["私人聊天内容", "心理健康信息"],
  },
  {
    id: "repair",
    title: "宿舍门锁报修",
    description: "后勤系统要求补充门牌照片，任务已暂停。",
    category: "宿舍服务",
    status: "WAITING",
    statusLabel: "等待系统",
    updatedAt: "昨天 18:10",
    owner: "后勤服务中心",
    receipt: "HQ-DEMO-260720-114",
    timeline: [
      { time: "18:03", title: "已提交演示工单", detail: "问题：门锁无法正常闭合", done: true },
      { time: "18:10", title: "等待补充材料", detail: "需要由你上传门牌照片", done: true },
      { time: "—", title: "尚未派单", detail: "补充材料后继续流转", done: false },
    ],
    dataUsed: ["宿舍楼栋", "房间号", "联系电话"],
    dataExcluded: ["相册其他照片", "个人对话", "心理健康信息"],
  },
  {
    id: "schedule",
    title: "每天 07:30 整理今日课程",
    description: "在上课日前生成课程、地点与出发提醒。",
    category: "课程日程",
    status: "SCHEDULED",
    statusLabel: "定时任务",
    updatedAt: "下次明天 07:30",
    owner: "个人 Agent",
    timeline: [
      { time: "7 月 18 日", title: "定时任务已创建", detail: "仅在有课日期执行", done: true },
      { time: "每天 07:30", title: "自动查询课表", detail: "结果只发送给你的个人工作台", done: false },
    ],
    dataUsed: ["个人课表", "校区", "上课地点"],
    dataExcluded: ["实时位置", "个人对话", "心理健康信息"],
  },
  {
    id: "venue",
    title: "图书馆协作空间预约",
    description: "已完成 7 月 21 日 16:30–18:00 的演示预约。",
    category: "场地预约",
    status: "COMPLETED",
    statusLabel: "已完成",
    updatedAt: "昨天 16:12",
    owner: "图书馆",
    receipt: "JNU-DEMO-LIB-8842",
    timeline: [
      { time: "16:08", title: "已选择空间", detail: "番禺校区图书馆协作空间 3", done: true },
      { time: "16:10", title: "你已确认预约", detail: "使用时间 16:30–18:00", done: true },
      { time: "16:12", title: "演示预约完成", detail: "已生成本地演示回执", done: true },
    ],
    dataUsed: ["姓名", "学号", "预约时段"],
    dataExcluded: ["个人对话", "个人知识库", "心理健康信息"],
  },
];

const STATUS_FILTERS: Array<{ id: "ALL" | TaskStatus; label: string }> = [
  { id: "ALL", label: "全部任务" },
  { id: "DRAFT", label: "草稿" },
  { id: "NEEDS_CONFIRMATION", label: "需要确认" },
  { id: "RUNNING", label: "正在执行" },
  { id: "WAITING", label: "等待系统" },
  { id: "SCHEDULED", label: "定时任务" },
  { id: "COMPLETED", label: "已完成" },
  { id: "CANCELLED", label: "已取消" },
];

function AgentTasksContent() {
  const [tasks, setTasks] = useState(INITIAL_TASKS);
  const [activeFilter, setActiveFilter] = useState<"ALL" | TaskStatus>("ALL");
  const [selectedTaskId, setSelectedTaskId] = useState("certificate");
  const [showLaunchNote, setShowLaunchNote] = useState(false);
  const [certificateAuthorized, setCertificateAuthorized] = useState(false);
  const [certificateGenerated, setCertificateGenerated] = useState(false);
  const [cancelConfirmTaskId, setCancelConfirmTaskId] = useState<string | null>(null);
  const [showCreateDrawer, setShowCreateDrawer] = useState(false);
  const [createMode, setCreateMode] = useState<"TEMPLATE" | "CUSTOM">("TEMPLATE");
  const [createTemplateId, setCreateTemplateId] = useState("certificate");
  const [createTitle, setCreateTitle] = useState("申请在读证明");
  const [createGoal, setCreateGoal] = useState(CREATE_TEMPLATE_DETAILS.certificate.goal);
  const [createExecution, setCreateExecution] = useState<"NOW" | "SCHEDULED" | "RECURRING">("NOW");
  const [createScheduleAt, setCreateScheduleAt] = useState("2026-07-23T09:00");
  const [createRecurrence, setCreateRecurrence] = useState("每个工作日 07:30");
  const [createNotify, setCreateNotify] = useState(true);
  const [createAuthorized, setCreateAuthorized] = useState(false);

  const filteredTasks = useMemo(
    () => activeFilter === "ALL" ? tasks : tasks.filter((task) => task.status === activeFilter),
    [activeFilter, tasks],
  );
  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0];
  const activeTimelineIndex = selectedTask.timeline.findIndex((step) => !step.done);
  const selectedCreateDetails = CREATE_TEMPLATE_DETAILS[createTemplateId];

  useEffect(() => {
    if (!showCreateDrawer) return;
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setShowCreateDrawer(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [showCreateDrawer]);

  const resetCreateForm = () => {
    setCreateMode("TEMPLATE");
    setCreateTemplateId("certificate");
    setCreateTitle("申请在读证明");
    setCreateGoal(CREATE_TEMPLATE_DETAILS.certificate.goal);
    setCreateExecution("NOW");
    setCreateScheduleAt("2026-07-23T09:00");
    setCreateRecurrence("每个工作日 07:30");
    setCreateNotify(true);
    setCreateAuthorized(false);
  };

  const openCreateDrawer = () => {
    resetCreateForm();
    setShowCreateDrawer(true);
  };

  const selectCreateTemplate = (templateId: string) => {
    const template = QUICK_TASKS.find((task) => task.id === templateId);
    const details = CREATE_TEMPLATE_DETAILS[templateId];
    if (!template || !details) return;
    setCreateTemplateId(templateId);
    setCreateTitle(template.title === "查询课程" ? "整理今日课程安排" : template.title === "通知摘要" ? "生成校园通知摘要" : template.title);
    setCreateGoal(details.goal);
    setCreateAuthorized(false);
  };

  const switchCreateMode = (mode: "TEMPLATE" | "CUSTOM") => {
    setCreateMode(mode);
    setCreateAuthorized(false);
    if (mode === "CUSTOM") {
      setCreateTitle("");
      setCreateGoal("");
    } else {
      selectCreateTemplate(createTemplateId || "certificate");
    }
  };

  const createNewTask = (saveAsDraft: boolean) => {
    const title = createTitle.trim();
    const goal = createGoal.trim();
    if (!title || !goal || (!saveAsDraft && !createAuthorized)) return;
    const id = `created-${Date.now()}`;
    const scheduled = createExecution !== "NOW";
    const status: TaskStatus = saveAsDraft ? "DRAFT" : scheduled ? "SCHEDULED" : "RUNNING";
    const statusLabel = saveAsDraft ? "草稿" : scheduled ? "定时任务" : "正在执行";
    const scheduleDetail = createExecution === "SCHEDULED" ? `计划执行：${createScheduleAt.replace("T", " ")}` : createExecution === "RECURRING" ? `执行周期：${createRecurrence}` : "Agent 已开始整理任务所需信息";
    const details = createMode === "TEMPLATE" ? selectedCreateDetails : null;
    const newTask: AgentTask = {
      id,
      title,
      description: saveAsDraft ? "任务配置已保存为草稿，尚未交给 Agent 执行。" : goal,
      category: details?.category ?? "自定义任务",
      status,
      statusLabel,
      updatedAt: "刚刚",
      owner: details?.owner ?? "个人 Agent",
      timeline: saveAsDraft
        ? [{ time: "刚刚", title: "任务草稿已保存", detail: "尚未授权数据或开始执行", done: true }, { time: "—", title: "等待开始", detail: "你可以稍后继续配置", done: false }]
        : [{ time: "刚刚", title: "任务已创建", detail: scheduleDetail, done: true }, { time: scheduled ? "计划" : "进行中", title: scheduled ? "等待计划时间" : "Agent 正在执行", detail: createNotify ? "完成后将通知你" : "完成后仅更新任务状态", done: false }],
      dataUsed: details?.dataUsed ?? ["任务目标", "执行时间"],
      dataExcluded: ["个人对话", "个人知识库", "心理健康信息"],
    };
    setTasks((current) => [newTask, ...current]);
    setActiveFilter("ALL");
    setSelectedTaskId(id);
    setCancelConfirmTaskId(null);
    setShowCreateDrawer(false);
  };

  const handleCreateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createNewTask(false);
  };

  const selectFilter = (filter: "ALL" | TaskStatus) => {
    setCancelConfirmTaskId(null);
    setActiveFilter(filter);
    const next = filter === "ALL" ? tasks[0] : tasks.find((task) => task.status === filter);
    if (next) setSelectedTaskId(next.id);
  };

  const openQuickTask = (taskId: string) => {
    const next = tasks.find((task) => task.id === taskId);
    if (!next) return;
    setActiveFilter("ALL");
    setCancelConfirmTaskId(null);
    setSelectedTaskId(next.id);
    setShowLaunchNote(true);
    window.setTimeout(() => setShowLaunchNote(false), 2400);
  };

  const confirmSelectedTask = () => {
    if (selectedTask.id === "certificate" && !certificateAuthorized) return;
    if (selectedTask.id === "certificate") setCertificateGenerated(true);
    setTasks((current) => current.map((task) => task.id === selectedTask.id ? {
      ...task,
      status: "COMPLETED",
      statusLabel: "已完成",
      updatedAt: "刚刚",
      receipt: "JNU-DEMO-20260721-018",
      description: task.id === "certificate"
        ? "演示在读证明 PDF 已生成，可预览或下载；未向真实校园系统提交。"
        : "已完成本地演示确认并生成回执；未向真实校园系统提交。",
      timeline: [
        ...task.timeline.filter((step) => step.title !== "尚未提交").map((step) => ({ ...step, done: true })),
        { time: "刚刚", title: task.id === "certificate" ? "PDF 已生成" : "你已完成演示确认", detail: "已生成本地演示回执，未提交真实申请", done: true },
      ],
    } : task));
  };

  const cancelSelectedTask = () => {
    setTasks((current) => current.map((task) => task.id === selectedTask.id ? {
      ...task,
      status: "CANCELLED",
      statusLabel: "已取消",
      updatedAt: "刚刚",
      description: "任务已由你取消，Agent 已停止后续执行；已有过程记录将保留用于审计。",
      timeline: [
        ...task.timeline.filter((step) => step.done),
        { time: "刚刚", title: "任务已取消", detail: "由你主动取消，未继续提交或调用校园系统", done: true },
      ],
    } : task));
    if (selectedTask.id === "certificate") {
      setCertificateAuthorized(false);
      setCertificateGenerated(false);
    }
    setCancelConfirmTaskId(null);
  };

  return (
    <div className="agent-task-center">
      <header className="agent-task-page-header">
        <div className="agent-chat-identity">
          <span className="agent-chat-avatar" aria-hidden="true">AT</span>
          <span><strong>Agent 任务中心</strong><small><i aria-hidden="true" />查询、办理、委托和持续跟进</small></span>
        </div>
        <nav className="agent-workspace-tabs" aria-label="个人工作台视图">
          <Link href="/workspace">工作台</Link>
          <span aria-current="page">Agent 任务</span>
        </nav>
        <span className="agent-task-demo-badge">演示工作流</span>
      </header>

      <main className="agent-task-page-body">
        <section className="agent-task-hero" aria-labelledby="agent-task-title">
          <div><span>AGENT TASKS</span><h1 id="agent-task-title">把校园事务交给 Agent 跟进</h1><p>选择一个任务，Agent 会先收集必要信息、生成草稿并展示执行过程；提交、发送等重要操作仍由你最终确认。</p></div>
          <aside><strong>{tasks.filter((task) => task.status === "NEEDS_CONFIRMATION").length}</strong><span>项任务需要你确认</span></aside>
        </section>

        <section className="agent-task-launch" aria-labelledby="quick-task-title">
          <header><div><span>QUICK START</span><h2 id="quick-task-title">快速发起</h2></div><p>{showLaunchNote ? "已为你打开对应任务详情" : "不用重复输入常见事务"}</p></header>
          <div>
            {QUICK_TASKS.map((task) => (
              <button key={task.id} type="button" onClick={() => openQuickTask(task.targetTask)}>
                <span aria-hidden="true">{task.icon}</span>
                <div><small>{task.type}</small><strong>{task.title}</strong><p>{task.detail}</p></div>
                <i aria-hidden="true">→</i>
              </button>
            ))}
          </div>
        </section>

        <section className="agent-task-board" aria-label="任务列表和详情">
          <aside className="agent-task-sidebar">
            <header><div><span>MY TASKS</span><h2>我的任务</h2></div><button type="button" className="agent-task-create-button" onClick={openCreateDrawer}><i aria-hidden="true">＋</i>创建任务</button></header>
            <nav aria-label="按任务状态筛选">
              {STATUS_FILTERS.map((filter) => {
                const count = filter.id === "ALL" ? tasks.length : tasks.filter((task) => task.status === filter.id).length;
                return <button key={filter.id} type="button" className={activeFilter === filter.id ? "is-active" : ""} onClick={() => selectFilter(filter.id)}><span>{filter.label}</span><small>{count}</small></button>;
              })}
            </nav>
            <div className="agent-task-list">
              {filteredTasks.length === 0 && <p className="agent-task-empty">这个状态下暂时没有任务</p>}
              {filteredTasks.map((task) => (
                <button key={task.id} type="button" className={selectedTask.id === task.id ? "is-active" : ""} onClick={() => { setSelectedTaskId(task.id); setCancelConfirmTaskId(null); }}>
                  <i className={`is-${task.status.toLowerCase()}`} aria-hidden="true" />
                  <div><span>{task.category}</span><strong>{task.title}</strong><small>{task.updatedAt}</small></div>
                  <em className={`is-${task.status.toLowerCase()}`}>{task.statusLabel}</em>
                </button>
              ))}
            </div>
          </aside>

          <article className="agent-task-detail">
            <header>
              <div><span>{selectedTask.category} · {selectedTask.owner}</span><h2>{selectedTask.title}</h2><p>{selectedTask.description}</p></div>
              <em className={`is-${selectedTask.status.toLowerCase()}`}>{selectedTask.statusLabel}</em>
            </header>

            {selectedTask.receipt && <div className="agent-task-receipt"><span aria-hidden="true">✓</span><p><small>演示回执</small><strong>{selectedTask.receipt}</strong></p><button type="button">复制编号</button></div>}

            {selectedTask.id === "certificate" && selectedTask.status !== "CANCELLED" && (
              <section className={`agent-certificate-demo${certificateGenerated ? " is-generated" : ""}`} aria-labelledby="certificate-demo-title">
                <header>
                  <div><span>ENROLLMENT CERTIFICATE DEMO</span><h3 id="certificate-demo-title">申请在读证明</h3><p>Agent 已整理必要信息，请核对后生成带演示标识的 PDF。</p></div>
                  <ol aria-label="证明生成步骤">
                    <li className="is-done"><i>1</i><span>核对信息</span></li>
                    <li className={certificateAuthorized || certificateGenerated ? "is-done" : "is-current"}><i>2</i><span>确认生成</span></li>
                    <li className={certificateGenerated ? "is-done" : ""}><i>3</i><span>下载 PDF</span></li>
                  </ol>
                </header>

                {!certificateGenerated ? (
                  <div className="agent-certificate-review">
                    <dl>
                      <div><dt>申请人</dt><dd>Alice Chen（演示学生）</dd></div>
                      <div><dt>学号</dt><dd>2026100001</dd></div>
                      <div><dt>学院与专业</dt><dd>信息科学技术学院 · 软件工程</dd></div>
                      <div><dt>在读状态</dt><dd><span>在籍</span></dd></div>
                    </dl>
                    <div className="agent-certificate-options">
                      <label><span>证明用途</span><select defaultValue="internship"><option value="internship">实习材料演示</option></select></label>
                      <label><span>文件语言</span><select defaultValue="zh"><option value="zh">中文</option></select></label>
                      <label><span>文件格式</span><select defaultValue="pdf"><option value="pdf">PDF · A4</option></select></label>
                    </div>
                    <label className="agent-certificate-consent">
                      <input type="checkbox" checked={certificateAuthorized} onChange={(event) => setCertificateAuthorized(event.target.checked)} />
                      <span><strong>我已核对以上演示信息，并授权本任务使用这些字段生成 PDF</strong><small>不会读取个人对话、个人知识库或心理健康信息。</small></span>
                    </label>
                  </div>
                ) : (
                  <div className="agent-certificate-result">
                    <span aria-hidden="true">PDF</span>
                    <div><small>已生成 · JNU-DEMO-20260721-018</small><strong>在读证明（演示件）.pdf</strong><p>A4 · 中文 · 约 151 KB · 带“非官方证明”水印</p></div>
                    <div><a href="/demo/enrollment-certificate-demo.pdf" target="_blank" rel="noreferrer">预览 PDF</a><a className="is-primary" href="/demo/enrollment-certificate-demo.pdf" download="暨南大学在读证明-演示件.pdf">下载 PDF</a></div>
                  </div>
                )}

                <footer><i aria-hidden="true">!</i><p><strong>演示文件不具有证明效力</strong><span>真实在读证明必须由暨南大学相应责任部门审核并通过学校正式渠道签发。</span></p></footer>
              </section>
            )}

            <section className="agent-task-timeline" aria-labelledby="task-progress-title">
              <header><h3 id="task-progress-title">执行进度</h3><span>最近更新 {selectedTask.updatedAt}</span></header>
              <ol>
                {selectedTask.timeline.map((step, index) => <li key={`${step.time}-${step.title}-${index}`} className={step.done ? "is-done" : index === activeTimelineIndex ? "is-current" : ""}><time>{step.time}</time><i aria-hidden="true">{step.done ? "✓" : ""}</i><div><strong>{step.title}{index === activeTimelineIndex && <em>当前步骤</em>}</strong><p>{step.detail}</p></div></li>)}
              </ol>
            </section>

            <section className="agent-task-data" aria-labelledby="task-data-title">
              <header><span aria-hidden="true">盾</span><div><h3 id="task-data-title">本任务的数据使用范围</h3><p>只读取完成当前任务所必需的信息</p></div></header>
              <div><p><strong>本次使用</strong>{selectedTask.dataUsed.map((item) => <span key={item}>{item}</span>)}</p><p><strong>不会读取</strong>{selectedTask.dataExcluded.map((item) => <span key={item}>{item}</span>)}</p></div>
            </section>

            <footer>
              <p><strong>{selectedTask.status === "CANCELLED" ? "任务已停止" : "重要操作由你决定"}</strong><span>{selectedTask.status === "CANCELLED" ? "取消记录已保留，Agent 不会继续执行这项任务。" : "当前为界面演示，不会向暨南大学真实系统提交申请。"}</span></p>
              {cancelConfirmTaskId === selectedTask.id ? (
                <div className="agent-task-cancel-confirm" role="status"><span>确认取消这项任务？</span><button type="button" onClick={() => setCancelConfirmTaskId(null)}>继续任务</button><button type="button" className="is-danger" onClick={cancelSelectedTask}>确认取消</button></div>
              ) : selectedTask.status !== "COMPLETED" && selectedTask.status !== "CANCELLED" ? (
                <div><button type="button" className="is-cancel" onClick={() => setCancelConfirmTaskId(selectedTask.id)}>取消任务</button>{selectedTask.status === "NEEDS_CONFIRMATION" && <button type="button" className="is-primary" onClick={confirmSelectedTask} disabled={selectedTask.id === "certificate" && !certificateAuthorized}>{selectedTask.id === "certificate" ? "生成演示证明" : "确认演示提交"}</button>}</div>
              ) : null}
            </footer>
          </article>
        </section>
      </main>

      {showCreateDrawer && (
        <div className="agent-task-drawer-backdrop" role="presentation" onMouseDown={() => setShowCreateDrawer(false)}>
          <aside className="agent-task-create-drawer" role="dialog" aria-modal="true" aria-labelledby="create-agent-task-title" onMouseDown={(event) => event.stopPropagation()}>
            <header>
              <div><span>NEW AGENT TASK</span><h2 id="create-agent-task-title">创建 Agent 任务</h2><p>配置目标、执行方式和本次数据权限</p></div>
              <button type="button" aria-label="关闭创建任务面板" onClick={() => setShowCreateDrawer(false)}>×</button>
            </header>

            <form onSubmit={handleCreateSubmit}>
              <div className="agent-task-create-tabs" role="tablist" aria-label="任务创建方式">
                <button type="button" role="tab" aria-selected={createMode === "TEMPLATE"} className={createMode === "TEMPLATE" ? "is-active" : ""} onClick={() => switchCreateMode("TEMPLATE")}>常用模板</button>
                <button type="button" role="tab" aria-selected={createMode === "CUSTOM"} className={createMode === "CUSTOM" ? "is-active" : ""} onClick={() => switchCreateMode("CUSTOM")}>自定义任务</button>
              </div>

              <div className="agent-task-create-scroll">
                {createMode === "TEMPLATE" ? (
                  <section className="agent-task-template-picker" aria-labelledby="task-template-heading">
                    <header><h3 id="task-template-heading">选择任务模板</h3><span>模板会自动填写任务目标</span></header>
                    <div>{QUICK_TASKS.map((template) => <button key={template.id} type="button" className={createTemplateId === template.id ? "is-selected" : ""} onClick={() => selectCreateTemplate(template.id)}><span aria-hidden="true">{template.icon}</span><p><strong>{template.title}</strong><small>{template.type} · {template.detail}</small></p><i aria-hidden="true">{createTemplateId === template.id ? "✓" : ""}</i></button>)}</div>
                  </section>
                ) : (
                  <section className="agent-task-custom-intro"><span aria-hidden="true">AI</span><p><strong>用一句话描述希望 Agent 完成的目标</strong><small>这里创建的是可跟踪任务，不会进入问答聊天记录。</small></p></section>
                )}

                <section className="agent-task-create-section" aria-labelledby="task-config-heading">
                  <header><h3 id="task-config-heading">任务配置</h3><span>创建后仍可取消</span></header>
                  <label><span>任务名称</span><input value={createTitle} onChange={(event) => setCreateTitle(event.target.value)} placeholder="例如：整理明天的课程安排" maxLength={40} /></label>
                  <label><span>任务目标</span><textarea value={createGoal} onChange={(event) => setCreateGoal(event.target.value)} placeholder="说明希望 Agent 做什么、产出什么结果" rows={3} maxLength={240} /></label>
                </section>

                <section className="agent-task-create-section" aria-labelledby="task-execution-heading">
                  <header><h3 id="task-execution-heading">执行方式</h3><span>选择任务何时开始</span></header>
                  <div className="agent-task-execution-options">
                    <label><input type="radio" name="execution" checked={createExecution === "NOW"} onChange={() => setCreateExecution("NOW")} /><span><strong>立即执行</strong><small>创建后马上开始</small></span></label>
                    <label><input type="radio" name="execution" checked={createExecution === "SCHEDULED"} onChange={() => setCreateExecution("SCHEDULED")} /><span><strong>指定时间</strong><small>到达时间后开始</small></span></label>
                    <label><input type="radio" name="execution" checked={createExecution === "RECURRING"} onChange={() => setCreateExecution("RECURRING")} /><span><strong>周期执行</strong><small>按固定周期重复</small></span></label>
                  </div>
                  {createExecution === "SCHEDULED" && <label><span>计划执行时间</span><input type="datetime-local" value={createScheduleAt} onChange={(event) => setCreateScheduleAt(event.target.value)} /></label>}
                  {createExecution === "RECURRING" && <label><span>执行周期</span><select value={createRecurrence} onChange={(event) => setCreateRecurrence(event.target.value)}><option>每个工作日 07:30</option><option>每天 20:00</option><option>每周一 08:00</option></select></label>}
                  <label className="agent-task-notify-option"><input type="checkbox" checked={createNotify} onChange={(event) => setCreateNotify(event.target.checked)} /><span><strong>完成后通知我</strong><small>结果会进入消息与通知</small></span></label>
                </section>

                <section className="agent-task-create-permission" aria-labelledby="task-permission-heading">
                  <header><span aria-hidden="true">盾</span><div><h3 id="task-permission-heading">本次数据权限</h3><p>只使用完成这项任务所必需的信息</p></div></header>
                  <div><p><strong>计划使用</strong>{(createMode === "TEMPLATE" ? selectedCreateDetails?.dataUsed ?? [] : ["任务目标", "执行时间"]).map((item) => <span key={item}>{item}</span>)}</p><p><strong>明确不读取</strong><span>个人对话</span><span>个人知识库</span><span>心理健康信息</span></p></div>
                  <label><input type="checkbox" checked={createAuthorized} onChange={(event) => setCreateAuthorized(event.target.checked)} /><span>我了解并同意本次任务使用以上数据范围</span></label>
                </section>

                <aside className="agent-task-create-note"><i aria-hidden="true">!</i><p><strong>办理类任务仍需要你最终确认</strong><span>Agent 可以准备材料和草稿，但不会自行提交申请、发送消息或取消预约。</span></p></aside>
              </div>

              <footer><button type="button" onClick={() => setShowCreateDrawer(false)}>取消</button><span /><button type="button" onClick={() => createNewTask(true)} disabled={!createTitle.trim() || !createGoal.trim()}>保存为草稿</button><button type="submit" className="is-primary" disabled={!createTitle.trim() || !createGoal.trim() || !createAuthorized}>创建并开始</button></footer>
            </form>
          </aside>
        </div>
      )}
    </div>
  );
}

export default function AgentTasksPage() {
  return <AppShell requireAuth><AgentTasksContent /></AppShell>;
}
