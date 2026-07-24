'use client';

import Link from 'next/link';
import { useMemo, useState, type ReactNode } from 'react';
import { AppShell } from '@/components/app/AppShell';
import { useAuth } from '@/lib/auth';

type AgentView = 'overview' | 'skills' | 'connections' | 'automations' | 'runs' | 'runtime';

interface NavItem {
  id: AgentView;
  label: string;
  description: string;
  icon: ReactNode;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: 'overview',
    label: '运行概览',
    description: '状态与待确认事项',
    icon: (
      <>
        <circle cx="10" cy="10" r="6.5" />
        <path d="M10 6.5v3.8l2.5 1.5" />
      </>
    ),
  },
  {
    id: 'skills',
    label: '能力与 Skills',
    description: '管理 Agent 能做什么',
    badge: '8',
    icon: (
      <>
        <path d="m10 2.8 1.8 4.4 4.7.4-3.6 3 1.1 4.6-4-2.5-4 2.5 1.1-4.6-3.6-3 4.7-.4z" />
      </>
    ),
  },
  {
    id: 'connections',
    label: '工具与连接',
    description: '校园系统和外部服务',
    badge: '6',
    icon: (
      <>
        <path d="M7.5 6.5 5.8 4.8a2.1 2.1 0 0 0-3 3l2.5 2.5a2.1 2.1 0 0 0 3 0l1-1" />
        <path d="m12.5 13.5 1.7 1.7a2.1 2.1 0 0 0 3-3l-2.5-2.5a2.1 2.1 0 0 0-3 0l-1 1M7 13l6-6" />
      </>
    ),
  },
  {
    id: 'automations',
    label: '自动任务',
    description: '计划、周期与交付',
    badge: '3',
    icon: (
      <>
        <rect x="3.5" y="4.5" width="13" height="12" rx="2" />
        <path d="M6.5 2.8v3M13.5 2.8v3M3.5 8h13M7 11h2M11 11h2M7 14h2" />
      </>
    ),
  },
  {
    id: 'runs',
    label: '运行与审计',
    description: '执行过程可追溯',
    badge: '1',
    icon: (
      <>
        <path d="M5 3.5h8l2 2v11H5zM13 3.5v3h3" />
        <path d="M7.5 10h5M7.5 13h5M7.5 7h2" />
      </>
    ),
  },
  {
    id: 'runtime',
    label: '运行设置',
    description: '模型、环境与专项 Agent',
    icon: (
      <>
        <circle cx="10" cy="10" r="2.4" />
        <path d="M10 2.8v2M10 15.2v2M2.8 10h2M15.2 10h2M4.9 4.9l1.4 1.4M13.7 13.7l1.4 1.4M15.1 4.9l-1.4 1.4M6.3 13.7l-1.4 1.4" />
      </>
    ),
  },
];

const SKILLS = [
  {
    mark: '课',
    title: '课程助手',
    source: '暨南大学官方',
    description: '查询课表、课程地点、作业与成绩信息',
    permission: '读取课程信息',
    active: true,
    tone: 'green',
  },
  {
    mark: '知',
    title: '校园通知整理',
    source: '暨南大学官方',
    description: '合并学院、班级与课程消息，提取个人待办',
    permission: '读取校园消息',
    active: true,
    tone: 'blue',
  },
  {
    mark: '办',
    title: '校园事务助理',
    source: '暨南大学官方',
    description: '准备请假、证明、宿舍等事务的办理草稿',
    permission: '读取身份 · 写入前确认',
    active: true,
    tone: 'amber',
  },
  {
    mark: '协',
    title: '协作总结',
    source: 'CampusAgent',
    description: '整理群体意见、分歧与已达成的共识',
    permission: '读取参与的协作',
    active: true,
    tone: 'purple',
  },
];

const CONNECTIONS = [
  {
    mark: '教',
    title: '教务系统',
    detail: '课表、课程与成绩',
    level: '只读',
    status: '已连接',
    tone: 'green',
  },
  {
    mark: '邮',
    title: '校园邮箱',
    detail: '邮件摘要与待办识别',
    level: '只读',
    status: '已连接',
    tone: 'blue',
  },
  {
    mark: '历',
    title: '个人日历',
    detail: '读取日程，创建前确认',
    level: '需确认',
    status: '已连接',
    tone: 'purple',
  },
  {
    mark: '办',
    title: '统一办事大厅',
    detail: '查询进度与生成申请草稿',
    level: '需确认',
    status: '已连接',
    tone: 'amber',
  },
];

function ModuleIcon({ children }: { children: ReactNode }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      {children}
    </svg>
  );
}

function OverviewPanel({ displayName }: { displayName: string }) {
  return (
    <>
      <div className="agent-manager-section-heading">
        <div>
          <span>Agent 运行概览</span>
          <h2>{displayName}，你的 Agent 正在有序工作</h2>
          <p>重要操作都会停在确认环节，不会代替你做最终决定。</p>
        </div>
        <time>更新于 2 分钟前</time>
      </div>

      <div className="agent-manager-metrics">
        <article>
          <span className="is-green">✓</span>
          <div>
            <small>今日已完成</small>
            <strong>4</strong>
            <p>简报、课程提醒等</p>
          </div>
        </article>
        <article>
          <span className="is-blue">↗</span>
          <div>
            <small>正在执行</small>
            <strong>2</strong>
            <p>资料整理与进度查询</p>
          </div>
        </article>
        <article>
          <span className="is-amber">!</span>
          <div>
            <small>等待你确认</small>
            <strong>1</strong>
            <p>请假申请草稿</p>
          </div>
        </article>
        <article>
          <span className="is-purple">⌁</span>
          <div>
            <small>下次自动运行</small>
            <strong>08:00</strong>
            <p>明日校园简报</p>
          </div>
        </article>
      </div>

      <section className="agent-manager-block">
        <header>
          <div>
            <span>当前工作</span>
            <h3>任务队列</h3>
          </div>
          <Link href="/workspace">
            交办新任务 <i>→</i>
          </Link>
        </header>
        <div className="agent-task-list">
          <article>
            <span className="agent-task-symbol is-blue">资</span>
            <div>
              <strong>整理“软件工程”课程资料</strong>
              <p>正在归纳本周课件、作业要求和课堂通知</p>
            </div>
            <span className="agent-progress">
              <i style={{ width: '64%' }} />
            </span>
            <em>进行中 · 64%</em>
            <button aria-label="查看任务">›</button>
          </article>
          <article>
            <span className="agent-task-symbol is-green">报</span>
            <div>
              <strong>今日校园简报</strong>
              <p>已整理 3 条重要通知和 2 项个人待办</p>
            </div>
            <span className="agent-progress">
              <i style={{ width: '100%' }} />
            </span>
            <em className="is-done">已完成 · 08:02</em>
            <button aria-label="查看结果">›</button>
          </article>
          <article className="is-confirm">
            <span className="agent-task-symbol is-amber">假</span>
            <div>
              <strong>请假申请草稿</strong>
              <p>材料已准备完成，提交给任课教师前需要你确认</p>
            </div>
            <span className="agent-confirm-tag">尚未对外提交</span>
            <em>等待确认</em>
            <button aria-label="确认请假申请">确认</button>
          </article>
        </div>
      </section>

      <div className="agent-manager-two-column">
        <section className="agent-manager-block">
          <header>
            <div>
              <span>常用能力</span>
              <h3>已启用的校园 Skills</h3>
            </div>
            <button>管理全部</button>
          </header>
          <div className="agent-mini-skill-list">
            {SKILLS.slice(0, 3).map((skill) => (
              <div key={skill.title}>
                <span className={`is-${skill.tone}`}>{skill.mark}</span>
                <p>
                  <strong>{skill.title}</strong>
                  <small>{skill.description}</small>
                </p>
                <i>已启用</i>
              </div>
            ))}
          </div>
        </section>
        <section className="agent-manager-block">
          <header>
            <div>
              <span>接下来</span>
              <h3>自动任务</h3>
            </div>
            <button>查看计划</button>
          </header>
          <div className="agent-schedule-list">
            <div>
              <time>
                明天
                <br />
                <strong>08:00</strong>
              </time>
              <p>
                <strong>生成每日校园简报</strong>
                <small>使用：通知整理、课程助手</small>
              </p>
              <span>每天</span>
            </div>
            <div>
              <time>
                周日
                <br />
                <strong>20:30</strong>
              </time>
              <p>
                <strong>汇总本周未完成任务</strong>
                <small>结果仅发送至个人工作台</small>
              </p>
              <span>每周</span>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}

function SkillsPanel() {
  const [enabled, setEnabled] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(SKILLS.map((item) => [item.title, item.active]))
  );
  return (
    <>
      <div className="agent-manager-section-heading">
        <div>
          <span>能力管理</span>
          <h2>能力与 Skills</h2>
          <p>能力决定 Agent 会怎样完成任务；启用前先查看它需要的数据权限。</p>
        </div>
        <button className="agent-primary-action">＋ 添加能力</button>
      </div>
      <div className="agent-filter-row">
        <button className="is-active">已安装 8</button>
        <button>暨南官方</button>
        <button>个人能力</button>
        <label>
          <span>⌕</span>
          <input aria-label="搜索能力" placeholder="搜索能力" />
        </label>
      </div>
      <div className="agent-skill-grid">
        {SKILLS.map((skill) => (
          <article key={skill.title}>
            <header>
              <span className={`is-${skill.tone}`}>{skill.mark}</span>
              <div>
                <strong>{skill.title}</strong>
                <small>
                  <i>✓</i>
                  {skill.source}
                </small>
              </div>
              <button
                className={`agent-switch${enabled[skill.title] ? ' is-on' : ''}`}
                onClick={() =>
                  setEnabled((value) => ({ ...value, [skill.title]: !value[skill.title] }))
                }
                aria-label={`${enabled[skill.title] ? '停用' : '启用'}${skill.title}`}
                aria-pressed={enabled[skill.title]}
              >
                <i />
              </button>
            </header>
            <p>{skill.description}</p>
            <footer>
              <span>权限 · {skill.permission}</span>
              <button>查看详情</button>
            </footer>
          </article>
        ))}
      </div>
      <div className="agent-catalog-callout">
        <span>＋</span>
        <div>
          <strong>需要更多能力？</strong>
          <p>从学校审核的能力库安装，或在隔离环境中添加自己的 Skill。</p>
        </div>
        <button>浏览能力库</button>
      </div>
    </>
  );
}

function ConnectionsPanel() {
  return (
    <>
      <div className="agent-manager-section-heading">
        <div>
          <span>工具与连接</span>
          <h2>工具与校园连接</h2>
          <p>控制 Agent 可以访问哪些系统，以及只能读取还是可以在确认后写入。</p>
        </div>
        <button className="agent-primary-action">＋ 添加连接</button>
      </div>
      <div className="agent-connection-list">
        {CONNECTIONS.map((item) => (
          <article key={item.title}>
            <span className={`is-${item.tone}`}>{item.mark}</span>
            <div>
              <strong>{item.title}</strong>
              <p>{item.detail}</p>
              <small>最近访问：今天 09:12</small>
            </div>
            <em className={item.level === '只读' ? 'is-read' : 'is-confirm'}>{item.level}</em>
            <i>
              <b />
              {item.status}
            </i>
            <button>管理</button>
          </article>
        ))}
      </div>
      <div className="agent-connector-note">
        <span>盾</span>
        <p>
          <strong>连接不等于无限访问</strong>
          <small>每次调用都会记录用途和数据类别；涉及提交、发送或修改的操作必须由你确认。</small>
        </p>
        <Link href="/memory">查看数据授权</Link>
      </div>
    </>
  );
}

function AutomationsPanel() {
  const [paused, setPaused] = useState(false);
  return (
    <>
      <div className="agent-manager-section-heading">
        <div>
          <span>自动任务</span>
          <h2>自动任务</h2>
          <p>让 Agent 按计划整理信息和跟进事务，所有任务都可以暂停或查看执行历史。</p>
        </div>
        <button className="agent-primary-action">＋ 新建自动任务</button>
      </div>
      <div className="agent-automation-summary">
        <div>
          <small>运行中</small>
          <strong>{paused ? 2 : 3}</strong>
        </div>
        <div>
          <small>本周已执行</small>
          <strong>12</strong>
        </div>
        <div>
          <small>成功完成</small>
          <strong>100%</strong>
        </div>
        <div>
          <small>需要确认</small>
          <strong>0</strong>
        </div>
      </div>
      <div className="agent-automation-list">
        <article>
          <span className="is-green">报</span>
          <div>
            <strong>每日校园简报</strong>
            <p>整理课程、学院通知和个人待办，发送到个人工作台</p>
            <small>使用 2 项能力 · 下次运行 明天 08:00</small>
          </div>
          <em>每天 08:00</em>
          <button className="agent-row-more">•••</button>
        </article>
        <article>
          <span className="is-blue">课</span>
          <div>
            <strong>课程开始前提醒</strong>
            <p>提前 20 分钟提醒上课地点，并附上相关课程资料</p>
            <small>使用 1 项能力 · 下次运行 今天 13:40</small>
          </div>
          <em>按课表运行</em>
          <button className="agent-row-more">•••</button>
        </article>
        <article className={paused ? 'is-paused' : ''}>
          <span className="is-purple">周</span>
          <div>
            <strong>每周任务回顾</strong>
            <p>汇总未完成作业、校园事项和协作承诺</p>
            <small>
              {paused ? '已暂停，恢复后重新计算运行时间' : '使用 3 项能力 · 下次运行 周日 20:30'}
            </small>
          </div>
          <em>{paused ? '已暂停' : '每周日'}</em>
          <button onClick={() => setPaused((value) => !value)}>{paused ? '恢复' : '暂停'}</button>
        </article>
      </div>
    </>
  );
}

function RunsPanel() {
  return (
    <>
      <div className="agent-manager-section-heading">
        <div>
          <span>运行与审计</span>
          <h2>运行与审计</h2>
          <p>查看 Agent 为什么访问数据、调用了什么能力，以及是否发生外部操作。</p>
        </div>
        <button>导出我的记录</button>
      </div>
      <div className="agent-run-filter">
        <button className="is-active">全部记录</button>
        <button>数据访问</button>
        <button>外部操作</button>
        <button>异常</button>
        <span>今天 · 7 月 20 日</span>
      </div>
      <div className="agent-timeline">
        <article>
          <time>09:16</time>
          <span className="is-amber">确</span>
          <div>
            <strong>生成请假申请草稿</strong>
            <p>使用校园事务助理，根据你在工作台提供的信息生成草稿。</p>
            <small>未提交 · 等待本人确认</small>
          </div>
          <button>查看过程</button>
        </article>
        <article>
          <time>09:13</time>
          <span className="is-blue">知</span>
          <div>
            <strong>读取 3 条学院通知</strong>
            <p>用途：生成今日校园简报；未读取私人会话和其他组织消息。</p>
            <small>数据范围 · 学院公开通知</small>
          </div>
          <button>查看过程</button>
        </article>
        <article>
          <time>09:12</time>
          <span className="is-green">课</span>
          <div>
            <strong>读取今日课表</strong>
            <p>用途：检查课程时间与个人日程是否冲突。</p>
            <small>数据范围 · 本人课程信息</small>
          </div>
          <button>查看过程</button>
        </article>
        <article>
          <time>08:02</time>
          <span className="is-purple">报</span>
          <div>
            <strong>每日校园简报执行完成</strong>
            <p>结果已发送至个人工作台，仅本人可见。</p>
            <small>耗时 18 秒 · 调用 2 项能力</small>
          </div>
          <button>查看结果</button>
        </article>
      </div>
    </>
  );
}

function RuntimePanel() {
  return (
    <>
      <div className="agent-manager-section-heading">
        <div>
          <span>高级设置</span>
          <h2>运行设置</h2>
          <p>管理底层运行环境和专项 Agent。默认配置已经适合大多数校园任务。</p>
        </div>
        <span className="agent-advanced-badge">高级设置</span>
      </div>
      <div className="agent-runtime-grid">
        <section>
          <header>
            <span>核</span>
            <div>
              <strong>Agent 运行核心</strong>
              <small>Hermes-compatible runtime</small>
            </div>
            <i>
              <b />
              运行正常
            </i>
          </header>
          <dl>
            <div>
              <dt>默认模型</dt>
              <dd>Campus General</dd>
            </div>
            <div>
              <dt>运行环境</dt>
              <dd>个人隔离空间</dd>
            </div>
            <div>
              <dt>自主等级</dt>
              <dd>建议与草稿</dd>
            </div>
          </dl>
          <button>配置运行环境</button>
        </section>
        <section>
          <header>
            <span>专</span>
            <div>
              <strong>专项 Agent</strong>
              <small>受限能力与独立任务上下文</small>
            </div>
            <i>3 个已启用</i>
          </header>
          <div className="agent-specialists">
            <span>课程 Agent</span>
            <span>事务 Agent</span>
            <span>协作 Agent</span>
          </div>
          <button>管理专项 Agent</button>
        </section>
        <section>
          <header>
            <span>忆</span>
            <div>
              <strong>记忆与上下文</strong>
              <small>长期记忆由你控制</small>
            </div>
            <i>
              <b />
              已开启
            </i>
          </header>
          <p>已保存学习偏好 4 项、校园习惯 3 项。敏感信息记忆保持关闭。</p>
          <Link href="/memory">
            前往“我的与隐私”管理 <i>→</i>
          </Link>
        </section>
        <section>
          <header>
            <span>界</span>
            <div>
              <strong>工具安全边界</strong>
              <small>写入、发送和提交均需确认</small>
            </div>
            <i>标准保护</i>
          </header>
          <p>文件、网络和校园服务按任务授权；Agent 无法自行扩大权限。</p>
          <button>查看安全策略</button>
        </section>
      </div>
    </>
  );
}

function AgentsContent() {
  const { user } = useAuth();
  const [view, setView] = useState<AgentView>('overview');
  const [active, setActive] = useState(true);
  const displayName = user?.display_name ?? '同学';
  const accountId = user?.email?.split('@')[0] ?? '2024100123';
  const currentNav = useMemo(() => NAV_ITEMS.find((item) => item.id === view), [view]);

  return (
    <div className="agent-manager">
      <header className="agent-manager-hero">
        <div className="agent-manager-identity">
          <span className="agent-manager-avatar">
            <i>CA</i>
            <b className={active ? '' : 'is-offline'} />
          </span>
          <div>
            <span>我的校园智能体</span>
            <h1>{displayName}的个人 Agent</h1>
            <p>
              CampusAgent · {accountId}　
              <span className={active ? '' : 'is-paused'}>{active ? '运行正常' : '已暂停'}</span>
              　·　已连接 6 项校园服务
            </p>
          </div>
        </div>
        <div className="agent-manager-hero-actions">
          <Link href="/workspace">
            进入个人工作台 <span>↗</span>
          </Link>
          <button onClick={() => setActive((value) => !value)}>
            {active ? '暂停 Agent' : '恢复 Agent'}
          </button>
          <button aria-label="更多 Agent 设置">•••</button>
        </div>
      </header>

      <div className="agent-manager-layout">
        <aside className="agent-manager-nav" aria-label="Agent 管理模块">
          <div>
            <span>管理中心</span>
            <strong>我的 Agent</strong>
            <small>使用 Agent 请前往个人工作台</small>
          </div>
          <nav>
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                className={view === item.id ? 'is-active' : ''}
                onClick={() => setView(item.id)}
                aria-current={view === item.id ? 'page' : undefined}
              >
                <span>
                  <ModuleIcon>{item.icon}</ModuleIcon>
                </span>
                <p>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </p>
                {item.badge && <em>{item.badge}</em>}
              </button>
            ))}
          </nav>
          <div className="agent-manager-nav-footer">
            <span>盾</span>
            <p>
              <strong>个人 Agent 由你控制</strong>
              <small>教师和管理员不能直接读取私人记忆</small>
            </p>
          </div>
        </aside>

        <main className="agent-manager-content" aria-label={currentNav?.label}>
          {view === 'overview' && <OverviewPanel displayName={displayName} />}
          {view === 'skills' && <SkillsPanel />}
          {view === 'connections' && <ConnectionsPanel />}
          {view === 'automations' && <AutomationsPanel />}
          {view === 'runs' && <RunsPanel />}
          {view === 'runtime' && <RuntimePanel />}
        </main>

        <aside className="agent-manager-inspector">
          <section>
            <header>
              <span className="agent-inspector-shield">盾</span>
              <div>
                <strong>当前安全边界</strong>
                <small>适用于所有 Agent 任务</small>
              </div>
            </header>
            <ul>
              <li>
                <i />
                仅访问你已授权的数据
              </li>
              <li>
                <i />
                发送、提交与修改前确认
              </li>
              <li>
                <i />
                心理健康信息不用于管理评价
              </li>
            </ul>
            <Link href="/memory">
              管理数据与授权 <span>→</span>
            </Link>
          </section>
          <section>
            <header>
              <span className="agent-inspector-clock">!</span>
              <div>
                <strong>1 项等待确认</strong>
                <small>Agent 已暂停在提交前</small>
              </div>
            </header>
            <div className="agent-inspector-pending">
              <span>请假申请草稿</span>
              <strong>尚未对外提交</strong>
              <p>检查时间、原因和涉及课程后再决定。</p>
              <button>现在检查</button>
            </div>
          </section>
          <section className="agent-inspector-note">
            <span>运行透明</span>
            <p>每次工具调用都会记录用途、数据类别与结果，但不在此展示私密内容。</p>
          </section>
        </aside>
      </div>
    </div>
  );
}

export default function AgentsPage() {
  return (
    <AppShell requireAuth>
      <AgentsContent />
    </AppShell>
  );
}
