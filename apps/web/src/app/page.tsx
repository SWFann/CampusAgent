"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app/AppShell";
import { useAuth } from "@/lib/auth";
import { apiGet } from "@/lib/api/client";
import type { AgentSummary, ConversationSummary, SceneSummary } from "@/lib/api/types";
import { useAsync } from "@/lib/useAsync";

interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
}

interface SceneListResponse {
  scenes: SceneSummary[];
  total: number;
}

interface AgentListResponse {
  agents: AgentSummary[];
  total: number;
}

type RequiredTaskStatus = "WAITING_INPUT" | "WAITING_INTENT_CONFIRM" | "WAITING_MATCH" | "NEGOTIATING" | "ACTION_REQUIRED" | "CONFIRMING" | "REMATCH_REQUIRED" | "SCHOOL_REVIEW" | "COMPLETED";
const REQUIRED_TASK_STORAGE_KEY = "campusagent:dorm-required-task";
const REQUIRED_TASK_HOME_STATE: Record<RequiredTaskStatus, { label: string; action: string; note: string; urgent?: boolean; complete?: boolean }> = {
  WAITING_INPUT: { label: "待表达需求", action: "立即办理", note: "确认授权范围并填写室友偏好" },
  WAITING_INTENT_CONFIRM: { label: "待本人确认", action: "继续确认", note: "确认 Agent 对个人需求的理解", urgent: true },
  WAITING_MATCH: { label: "等待匹配", action: "查看进度", note: "正在寻找符合硬性条件的候选室友" },
  NEGOTIATING: { label: "Agent 协商中", action: "查看协商", note: "成员 Agent 正在形成共同方案" },
  ACTION_REQUIRED: { label: "新增条件待决定", action: "立即处理", note: "谈判已暂停，等待你的明确选择", urgent: true },
  CONFIRMING: { label: "待确认室友组合", action: "确认结果", note: "室友建议已生成，需要本人决定", urgent: true },
  REMATCH_REQUIRED: { label: "待重新匹配", action: "重新匹配", note: "已退出上一轮，但宿舍安排仍需完成", urgent: true },
  SCHOOL_REVIEW: { label: "学校审核中", action: "查看进度", note: "成员已确认，等待住宿工作组审核" },
  COMPLETED: { label: "已完成", action: "查看结果", note: "宿舍安排已确认", complete: true },
};

type HomeIconName =
  | "home"
  | "spark"
  | "message"
  | "calendar"
  | "people"
  | "agent"
  | "shield"
  | "arrow"
  | "book"
  | "bell"
  | "task"
  | "building"
  | "file"
  | "clock";

function HomeIcon({ name }: { name: HomeIconName }) {
  const paths: Record<HomeIconName, ReactNode> = {
    home: <><path d="M3.5 9.2 10 3.8l6.5 5.4" /><path d="M5.5 8.2v8h9v-8M8.2 16.2v-5h3.6v5" /></>,
    spark: <><path d="m10 2 .9 4.2L15 7.5l-4.1 1.3L10 13l-.9-4.2L5 7.5l4.1-1.3z" /><path d="m15.5 12 .5 2 2 .5-2 .5-.5 2-.5-2-2-.5 2-.5z" /></>,
    message: <><path d="M3.5 4.5h13v9H9l-4.5 3v-3h-1z" /><path d="M7 8h6M7 10.5h4" /></>,
    calendar: <><rect x="3.5" y="4.5" width="13" height="12" rx="2" /><path d="M6.5 2.8v3M13.5 2.8v3M3.5 8h13M7 11h2M11 11h2M7 14h2" /></>,
    people: <><circle cx="7" cy="7" r="2.4" /><circle cx="14" cy="8" r="1.8" /><path d="M2.5 16c.5-3 2.1-4.5 4.6-4.5s4.1 1.5 4.6 4.5M12.5 12.2c2.8-.2 4.5 1.1 5 3.5" /></>,
    agent: <><circle cx="10" cy="10.5" r="6" /><path d="M7.5 10h.1M12.4 10h.1M7.8 13c1.4 1 3 1 4.4 0M10 2v2.5M6 3.2l1.2 2" /></>,
    shield: <><path d="M10 2.8 16 5v4.8c0 3.5-2.1 6-6 7.5-3.9-1.5-6-4-6-7.5V5z" /><path d="m7.3 10 1.8 1.8 3.8-4" /></>,
    arrow: <><path d="M4 10h11M11 6l4 4-4 4" /></>,
    book: <><path d="M3.5 4.2c2.4-.8 4.5-.3 6.5 1.1v11c-2-1.4-4.1-1.8-6.5-1zM16.5 4.2c-2.4-.8-4.5-.3-6.5 1.1v11c2-1.4 4.1-1.8 6.5-1z" /></>,
    bell: <><path d="M5 14h10l-1.2-1.8V8a3.8 3.8 0 0 0-7.6 0v4.2zM8.2 16c.8.9 2.8.9 3.6 0" /></>,
    task: <><rect x="3.5" y="3.5" width="13" height="13" rx="2" /><path d="m6.5 8 1.3 1.3 2.3-2.6M11.8 8h2M6.5 12h7.3" /></>,
    building: <><path d="M4 16.5V6.8L10 3l6 3.8v9.7M2.8 16.5h14.4" /><path d="M7 8.5h1M12 8.5h1M7 11.5h1M12 11.5h1M9 16.5v-3h2v3" /></>,
    file: <><path d="M5 2.8h6l4 4v10.4H5zM11 2.8v4h4" /><path d="M7.5 11h5M7.5 14h4" /></>,
    clock: <><circle cx="10" cy="10" r="6.5" /><path d="M10 6.5v4l2.8 1.7" /></>,
  };
  return <svg className="campus-home-icon" viewBox="0 0 20 20" aria-hidden="true">{paths[name]}</svg>;
}

function CapabilityTags({ items }: { items: string[] }) {
  return <div className="campus-capability-tags">{items.map((item) => <span key={item}>{item}</span>)}</div>;
}

function HomeContent() {
  const { user } = useAuth();
  const [requiredTaskStatus, setRequiredTaskStatus] = useState<RequiredTaskStatus>("WAITING_INPUT");
  useEffect(() => {
    try {
      const stored = JSON.parse(window.localStorage.getItem(REQUIRED_TASK_STORAGE_KEY) || "null") as { status?: RequiredTaskStatus } | null;
      if (stored?.status && REQUIRED_TASK_HOME_STATE[stored.status]) setRequiredTaskStatus(stored.status);
    } catch {
      setRequiredTaskStatus("WAITING_INPUT");
    }
  }, []);
  const { data: conversationData, loading: convLoading } = useAsync<ConversationListResponse>(
    async () => apiGet("/conversations", { page_size: "5" }),
    [],
  );
  const { data: sceneData, loading: sceneLoading } = useAsync<SceneListResponse>(
    async () => apiGet("/scenes"),
    [],
  );
  const { data: agentData, loading: agentLoading } = useAsync<AgentListResponse>(
    async () => {
      const list = await apiGet<AgentListResponse>("/agents");
      if (list.agents.length > 0) return list;
      const agent = await apiGet<AgentSummary>("/agents/me");
      return { agents: [agent], total: 1 };
    },
    [],
  );

  const conversations = conversationData?.conversations ?? [];
  const scenes = sceneData?.scenes ?? [];
  const agents = agentData?.agents ?? [];
  const unreadCount = conversations.reduce((total, item) => total + (item.unread_count ?? 0), 0);
  const activeAgent = agents.find((agent) => agent.is_active) ?? agents[0];
  const todayLabel = new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "long" }).format(new Date());
  const latestConversation = conversations[0];
  const activeScene = scenes[0];
  const requiredTask = REQUIRED_TASK_HOME_STATE[requiredTaskStatus];

  return (
    <div className="campus-home campus-home-rich">
      <section className="campus-welcome-hero" aria-labelledby="home-welcome-title">
        <div className="campus-welcome-copy">
          <span className="campus-welcome-date"><i aria-hidden="true" />{todayLabel} · 暨南大学</span>
          <h1 id="home-welcome-title">你好！{user?.display_name ?? "同学"}</h1>
          <p>让你的 Agent 帮你整理校园信息、参与协作，也把每一个真实需求带到合适的人面前。</p>
          <div className="campus-welcome-principle">
            <HomeIcon name="shield" />
            <span>你的表达由你掌控，重要决定始终由相应责任人确认</span>
          </div>
        </div>
        <div className="campus-welcome-glance" aria-label="个人校园概览">
          <div className="campus-glance-agent">
            <span className="campus-glance-orb"><HomeIcon name="agent" /></span>
            <div><small>个人 Agent</small><strong>{agentLoading ? "正在连接" : activeAgent?.name ?? "等待启用"}</strong></div>
            <span className="campus-live-state"><i aria-hidden="true" />{activeAgent?.is_active ? "在线" : "待启用"}</span>
          </div>
          <div className="campus-glance-stats">
            <Link href="/conversations"><strong>{convLoading ? "—" : unreadCount}</strong><span>未读消息</span></Link>
            <Link href="/scenes"><strong>{sceneLoading ? "—" : scenes.length}</strong><span>进行中协作</span></Link>
            <Link href="/agents"><strong>{agents.length || "—"}</strong><span>可用 Agent</span></Link>
          </div>
          <Link href="/agents" className="campus-talk-agent">和我的 Agent 对话 <HomeIcon name="arrow" /></Link>
        </div>
      </section>

      <section className={`campus-required-task${requiredTask.urgent ? " is-urgent" : ""}${requiredTask.complete ? " is-complete" : ""}`} aria-labelledby="home-required-dorm-title">
        <span className="campus-required-task-icon"><HomeIcon name="building" /><i>校</i></span>
        <div><small>新生必办 · 暨南大学住宿工作组</small><h2 id="home-required-dorm-title">新生宿舍共识安排</h2><p>{requiredTask.note}</p></div>
        <dl><div><dt>当前状态</dt><dd>{requiredTask.label}</dd></div><div><dt>截止时间</dt><dd>8月20日 18:00</dd></div></dl>
        <Link href="/scenes/dormitory-match">{requiredTask.action}<HomeIcon name="arrow" /></Link>
      </section>

      <header className="campus-capabilities-heading">
        <div>
          <span>CAMPUSAGENT 能为你做什么</span>
          <h2>从个人安排到校园协作，都在一个工作台里</h2>
        </div>
        <p>信息由 Agent 整理，事务由你确认，协作让每个人的需求都被看见。</p>
      </header>

      <div className="campus-capability-grid">
        <section className="campus-capability-card is-workspace" aria-labelledby="workspace-title">
          <header>
            <span className="campus-capability-icon"><HomeIcon name="home" /></span>
            <div><span>个人工作台</span><h2 id="workspace-title">管理属于你的校园一天</h2></div>
            <Link href="/agents" aria-label="进入个人工作台"><HomeIcon name="arrow" /></Link>
          </header>
          <p>个人 Agent 理解你的安排与授权范围，帮你梳理课程、信息和任务，但不会替你作出重要决定。</p>
          <div className="campus-workspace-tools">
            <Link href="/agents"><HomeIcon name="agent" /><span><strong>个人 Agent</strong><small>能力、记忆与授权</small></span></Link>
            <Link href="/conversations"><HomeIcon name="message" /><span><strong>与 Agent 对话</strong><small>表达需求和想法</small></span></Link>
            <Link href="/organizations"><HomeIcon name="book" /><span><strong>课程与成绩</strong><small>课程信息集中查看</small></span></Link>
            <Link href="/agents"><HomeIcon name="task" /><span><strong>安排 Agent 干活</strong><small>提交任务并最终确认</small></span></Link>
          </div>
          <div className="campus-daily-strip">
            <div><HomeIcon name="spark" /><span><small>每日简报</small><strong>{unreadCount > 0 ? `${unreadCount} 条重要消息待查看` : "今天暂无紧急消息"}</strong></span></div>
            <div><HomeIcon name="calendar" /><span><small>今日课程与日程</small><strong>由 Agent 按你的课表整理</strong></span></div>
          </div>
        </section>

        <section className="campus-capability-card is-notices" aria-labelledby="notices-title">
          <header>
            <span className="campus-capability-icon"><HomeIcon name="bell" /></span>
            <div><span>消息与通知</span><h2 id="notices-title">重要信息，不再淹没</h2></div>
            <Link href="/conversations" aria-label="进入消息与通知"><HomeIcon name="arrow" /></Link>
          </header>
          <p>汇集学院、课程、班级与个人通知，由 Agent 提炼重点、合并重复内容并提示待办。</p>
          <CapabilityTags items={["学院重大消息", "个人重要通知", "待办校园事务", "课程与班级", "Agent 消息摘要", "未读提醒"]} />
          <Link href="/conversations" className="campus-card-live-row">
            <span className="campus-mini-icon"><HomeIcon name="message" /></span>
            <span><small>最近消息</small><strong>{latestConversation?.title || "还没有新的校园消息"}</strong></span>
            <em>{unreadCount > 0 ? `${unreadCount} 条未读` : "已读完"}</em>
          </Link>
        </section>

        <section className="campus-capability-card is-services" aria-labelledby="services-title">
          <header>
            <span className="campus-capability-icon"><HomeIcon name="building" /></span>
            <div><span>校园事务</span><h2 id="services-title">少跑一步，进度清楚</h2></div>
            <Link href="/organizations" aria-label="进入校园事务"><HomeIcon name="arrow" /></Link>
          </header>
          <p>从课程任务到生活服务，快速找到办理入口、所需材料、负责部门和当前进度。</p>
          <CapabilityTags items={["课程任务", "请假", "证明开具", "申请审批", "宿舍服务", "场地预约", "校园服务", "办理进度", "学院资源"]} />
          <div className="campus-service-foot">
            <span><HomeIcon name="file" />统一办事入口</span>
            <span><HomeIcon name="clock" />过程状态可追踪</span>
            <Link href="/organizations">浏览全部服务 <HomeIcon name="arrow" /></Link>
          </div>
        </section>

        <section className="campus-capability-card is-collaboration" aria-labelledby="collaboration-title">
          <header>
            <span className="campus-capability-icon"><HomeIcon name="people" /></span>
            <div><span>协作空间</span><h2 id="collaboration-title">让不同声音形成共识</h2></div>
            <Link href="/scenes" aria-label="进入协作空间"><HomeIcon name="arrow" /></Link>
          </header>
          <p>在班级、社团、宿舍等群体中沟通。多个 Agent 汇总公开意见，帮助成员公平参与。</p>
          <CapabilityTags items={["班级群", "社团协作", "宿舍群聊", "创建协作群", "发起沟通", "Agent 共识摘要"]} />
          <Link href={activeScene?.scene_key === "dorm_dinner" ? "/scenes/dinner" : "/scenes"} className="campus-card-live-row">
            <span className="campus-mini-icon"><HomeIcon name="people" /></span>
            <span><small>正在参加</small><strong>{activeScene?.title || "暂时没有进行中的协作"}</strong></span>
            <em>{activeScene ? `${activeScene.participant_count ?? 0} 人参与` : "去创建"}</em>
          </Link>
        </section>
      </div>

      <footer className="campus-home-trust">
        <span><HomeIcon name="shield" /></span>
        <div><strong>CampusAgent 连接服务，但不越过边界</strong><small>私人 Agent 数据、心理健康信息与行政数据严格分域；教师和管理员不会因管理身份自动读取。</small></div>
        <Link href="/memory">管理我的数据 <HomeIcon name="arrow" /></Link>
      </footer>
    </div>
  );
}

export default function HomePage() {
  return <AppShell requireAuth><HomeContent /></AppShell>;
}
