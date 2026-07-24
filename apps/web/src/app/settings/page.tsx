'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { AppShell } from '@/components/app/AppShell';
import { useAuth, useIsAdmin } from '@/lib/auth';

type SettingsView =
  | 'overview'
  | 'account'
  | 'agent'
  | 'notifications'
  | 'privacy'
  | 'connections'
  | 'security'
  | 'appearance'
  | 'help'
  | 'governance';

interface SettingNavItem {
  id: SettingsView;
  label: string;
  description: string;
  icon: SettingsIconName;
  adminOnly?: boolean;
}

type SettingsIconName =
  | 'overview'
  | 'account'
  | 'agent'
  | 'notifications'
  | 'privacy'
  | 'connections'
  | 'security'
  | 'appearance'
  | 'help'
  | 'governance'
  | 'storage';

const SETTING_NAV: SettingNavItem[] = [
  { id: 'overview', label: '设置概览', description: '安全、授权与连接状态', icon: 'overview' },
  { id: 'account', label: '个人与校园身份', description: '账号、学院与联系方式', icon: 'account' },
  { id: 'agent', label: '我的 Agent', description: '行为、自动任务与确认边界', icon: 'agent' },
  {
    id: 'notifications',
    label: '通知与提醒',
    description: '消息渠道与免打扰',
    icon: 'notifications',
  },
  {
    id: 'privacy',
    label: '知识、记忆与隐私',
    description: '个人数据、授权与撤回',
    icon: 'privacy',
  },
  {
    id: 'connections',
    label: '权限与连接',
    description: '校园服务与外部工具',
    icon: 'connections',
  },
  { id: 'security', label: '账号与安全', description: '登录设备与二次确认', icon: 'security' },
  {
    id: 'appearance',
    label: '显示与辅助功能',
    description: '主题、字号与快捷键',
    icon: 'appearance',
  },
  { id: 'help', label: '帮助与关于', description: '指南、反馈与平台信息', icon: 'help' },
  {
    id: 'governance',
    label: '系统治理',
    description: '仅学校管理员可见',
    icon: 'governance',
    adminOnly: true,
  },
];

function SettingsIcon({ name }: { name: SettingsIconName }) {
  const paths: Record<SettingsIconName, ReactNode> = {
    overview: (
      <>
        <rect x="3.5" y="3.5" width="5" height="5" rx="1" />
        <rect x="11.5" y="3.5" width="5" height="5" rx="1" />
        <rect x="3.5" y="11.5" width="5" height="5" rx="1" />
        <rect x="11.5" y="11.5" width="5" height="5" rx="1" />
      </>
    ),
    account: (
      <>
        <circle cx="10" cy="7" r="3" />
        <path d="M4.5 16c.7-3 2.5-4.5 5.5-4.5s4.8 1.5 5.5 4.5" />
      </>
    ),
    agent: (
      <>
        <circle cx="10" cy="10.5" r="6" />
        <path d="M7.5 10h.1M12.4 10h.1M7.8 13c1.4 1 3 1 4.4 0M10 2v2.5" />
      </>
    ),
    notifications: (
      <>
        <path d="M5.5 8.5c0-2.8 1.6-4.5 4.5-4.5s4.5 1.7 4.5 4.5v3l1.5 2H4l1.5-2z" />
        <path d="M8 15.5c.5 1.4 3.5 1.4 4 0" />
      </>
    ),
    privacy: (
      <>
        <path d="M10 2.8 16 5v4.8c0 3.5-2.1 6-6 7.5-3.9-1.5-6-4-6-7.5V5z" />
        <path d="m7.3 10 1.8 1.8 3.8-4" />
      </>
    ),
    connections: (
      <>
        <path d="m8 12 4-4M6.8 14.8l-1 1a2.7 2.7 0 0 1-3.8-3.8l2.8-2.8a2.7 2.7 0 0 1 3.8 0M13.2 5.2l1-1A2.7 2.7 0 0 1 18 8l-2.8 2.8a2.7 2.7 0 0 1-3.8 0" />
      </>
    ),
    security: (
      <>
        <rect x="4.5" y="8.5" width="11" height="8" rx="2" />
        <path d="M7 8.5V6a3 3 0 0 1 6 0v2.5M10 12v1.5" />
      </>
    ),
    appearance: (
      <>
        <circle cx="10" cy="10" r="3" />
        <path d="M10 2.5v2M10 15.5v2M2.5 10h2M15.5 10h2M4.7 4.7l1.4 1.4M13.9 13.9l1.4 1.4M15.3 4.7l-1.4 1.4M6.1 13.9l-1.4 1.4" />
      </>
    ),
    help: (
      <>
        <circle cx="10" cy="10" r="7" />
        <path d="M7.8 7.5A2.3 2.3 0 0 1 10 6c1.4 0 2.4.8 2.4 2 0 1.7-2.4 1.8-2.4 3.4M10 14.2h.1" />
      </>
    ),
    governance: (
      <>
        <path d="M4 16.5V6.8L10 3l6 3.8v9.7M2.8 16.5h14.4" />
        <path d="M7 8.5h1M12 8.5h1M7 11.5h1M12 11.5h1M9 16.5v-3h2v3" />
      </>
    ),
    storage: (
      <>
        <ellipse cx="10" cy="5" rx="6" ry="2.5" />
        <path d="M4 5v5c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V5M4 10v5c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5v-5" />
      </>
    ),
  };
  return (
    <svg className="settings-line-icon" viewBox="0 0 20 20" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}) {
  return (
    <label className="settings-toggle">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        aria-label={label}
      />
      <span aria-hidden="true" />
    </label>
  );
}

function SettingRow({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="settings-row">
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
      <div className="settings-row-control">{children}</div>
    </div>
  );
}

function PanelHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <header className="settings-panel-heading">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
      <p>{description}</p>
    </header>
  );
}

function OverviewPanel({
  displayName,
  onNavigate,
}: {
  displayName: string;
  onNavigate: (view: SettingsView) => void;
}) {
  return (
    <>
      <PanelHeading
        eyebrow="设置概览"
        title={`${displayName}，你的设置状态良好`}
        description="集中查看账号安全、Agent 授权、校园连接与个人数据使用情况。"
      />
      <div className="settings-overview-grid">
        <button onClick={() => onNavigate('security')}>
          <span className="is-green">
            <SettingsIcon name="security" />
          </span>
          <div>
            <small>账号安全</small>
            <strong>良好</strong>
            <p>已绑定手机，最近登录正常</p>
          </div>
          <i>›</i>
        </button>
        <button onClick={() => onNavigate('privacy')}>
          <span className="is-blue">
            <SettingsIcon name="privacy" />
          </span>
          <div>
            <small>Agent 授权</small>
            <strong>6 项</strong>
            <p>1 项权限建议等待确认</p>
          </div>
          <i>›</i>
        </button>
        <button onClick={() => onNavigate('connections')}>
          <span className="is-purple">
            <SettingsIcon name="connections" />
          </span>
          <div>
            <small>校园系统连接</small>
            <strong>5 个</strong>
            <p>课表、图书馆等运行正常</p>
          </div>
          <i>›</i>
        </button>
        <button onClick={() => onNavigate('privacy')}>
          <span className="is-amber">
            <SettingsIcon name="storage" />
          </span>
          <div>
            <small>个人空间</small>
            <strong>1.4 GB</strong>
            <p>共 5 GB 加密存储空间</p>
          </div>
          <i>›</i>
        </button>
      </div>
      <section className="settings-section settings-priority">
        <header>
          <div>
            <span>建议检查</span>
            <h3>让 Agent 的权限保持清楚、适度</h3>
          </div>
          <em>1 项</em>
        </header>
        <SettingRow
          title="课程事务提交权限"
          description="Agent 可以生成课程事务草稿，但每次对外提交前都需要你本人确认。"
        >
          <button className="settings-text-button" onClick={() => onNavigate('connections')}>
            检查权限
          </button>
        </SettingRow>
      </section>
      <div className="settings-overview-columns">
        <section className="settings-section">
          <header>
            <div>
              <span>隐私边界</span>
              <h3>你的私人数据由你控制</h3>
            </div>
          </header>
          <ul className="settings-check-list">
            <li>
              <i />
              教师和管理员不能默认读取个人 Agent 记忆
            </li>
            <li>
              <i />
              心理健康信息与行政管理数据严格分域
            </li>
            <li>
              <i />
              发送、提交和修改均保留本人最终确认
            </li>
          </ul>
          <Link href="/memory">
            管理个人知识库 <span>→</span>
          </Link>
        </section>
        <section className="settings-section">
          <header>
            <div>
              <span>最近活动</span>
              <h3>账号与授权记录</h3>
            </div>
          </header>
          <div className="settings-activity">
            <p>
              <time>今天 09:12</time>
              <strong>个人 Agent 读取今日课表</strong>
              <small>用途：检查日程冲突</small>
            </p>
            <p>
              <time>昨天 21:06</time>
              <strong>新设备登录已确认</strong>
              <small>macOS · 广州</small>
            </p>
          </div>
          <button className="settings-text-button" onClick={() => onNavigate('security')}>
            查看全部记录
          </button>
        </section>
      </div>
    </>
  );
}

function AccountPanel({ displayName, email }: { displayName: string; email: string }) {
  return (
    <>
      <PanelHeading
        eyebrow="校园身份"
        title="个人与校园身份"
        description="校园身份由学校统一维护，个人联系方式和展示信息由你管理。"
      />
      <section className="settings-profile-card">
        <span>{displayName.slice(0, 1)}</span>
        <div>
          <strong>{displayName}</strong>
          <p>暨南大学 · 信息科学技术学院</p>
          <small>CampusAgent · {email.split('@')[0] || '2024100123'}</small>
        </div>
        <button>更换头像</button>
      </section>
      <section className="settings-section">
        <header>
          <div>
            <span>校园身份</span>
            <h3>学校同步信息</h3>
          </div>
          <em className="is-safe">已认证</em>
        </header>
        <SettingRow title="暨南大学账号" description="同时作为你的学号与统一身份账号">
          <b>{email}</b>
        </SettingRow>
        <SettingRow title="学院与专业" description="由学校组织系统同步，无法在此直接修改">
          <b>信息科学技术学院 · 软件工程</b>
        </SettingRow>
        <SettingRow title="班级" description="用于课程、通知和班级协作">
          <b>2024级软件工程1班</b>
        </SettingRow>
      </section>
      <section className="settings-section">
        <header>
          <div>
            <span>联系方式</span>
            <h3>验证与找回方式</h3>
          </div>
        </header>
        <SettingRow title="绑定手机" description="用于安全验证和重要事务提醒">
          <button>138••••1906　修改</button>
        </SettingRow>
        <SettingRow title="紧急联系方式" description="仅在本人授权的紧急支持流程中使用">
          <button>尚未填写　添加</button>
        </SettingRow>
      </section>
    </>
  );
}

function AgentPanel() {
  const [briefing, setBriefing] = useState(true);
  const [confirm, setConfirm] = useState(true);
  const [memory, setMemory] = useState(true);
  return (
    <>
      <PanelHeading
        eyebrow="我的 Agent"
        title="我的 Agent"
        description="设置 Agent 如何协助你，所有重要决定仍由你本人最终确认。"
      />
      <section className="settings-section">
        <header>
          <div>
            <span>基础行为</span>
            <h3>交流与工作方式</h3>
          </div>
          <Link href="/agents">进入 Agent 管理</Link>
        </header>
        <SettingRow title="称呼与表达" description="使用简体中文，表达清晰、温和并优先给出结论">
          <button>编辑偏好</button>
        </SettingRow>
        <SettingRow title="默认工作模式" description="查询可以直接完成，写入和提交先生成草稿">
          <select aria-label="默认工作模式">
            <option>建议与草稿</option>
            <option>仅查询</option>
          </select>
        </SettingRow>
        <SettingRow title="每日校园简报" description="每天 08:00 整理课程、通知和待办">
          <Toggle checked={briefing} onChange={setBriefing} label="每日校园简报" />
        </SettingRow>
      </section>
      <section className="settings-section">
        <header>
          <div>
            <span>安全边界</span>
            <h3>自主能力与个人控制</h3>
          </div>
        </header>
        <SettingRow
          title="重要操作需要确认"
          description="发送消息、提交申请、修改校园数据前必须询问你"
        >
          <Toggle checked={confirm} onChange={setConfirm} label="重要操作需要确认" />
        </SettingRow>
        <SettingRow title="使用长期记忆" description="仅使用你在个人知识库中允许的内容">
          <Toggle checked={memory} onChange={setMemory} label="使用长期记忆" />
        </SettingRow>
        <SettingRow title="自动任务" description="3 项自动任务正在运行，下次执行时间 08:00">
          <Link href="/agents">管理自动任务</Link>
        </SettingRow>
      </section>
    </>
  );
}

function NotificationsPanel() {
  const [states, setStates] = useState({
    school: true,
    college: true,
    course: true,
    affairs: true,
    scenes: true,
    agent: true,
  });
  const toggle = (key: keyof typeof states) => (value: boolean) =>
    setStates((current) => ({ ...current, [key]: value }));
  return (
    <>
      <PanelHeading
        eyebrow="通知与提醒"
        title="通知与提醒"
        description="选择消息的提醒方式。学校重要通知仍会保留在消息中心。"
      />
      <section className="settings-section">
        <header>
          <div>
            <span>消息类型</span>
            <h3>站内与设备提醒</h3>
          </div>
          <button>全部开启</button>
        </header>
        <SettingRow title="学校重要通知" description="校级制度、安全提醒和重大事项">
          <Toggle checked={states.school} onChange={toggle('school')} label="学校重要通知" />
        </SettingRow>
        <SettingRow title="学院与班级消息" description="学院通知、班级公告与教师沟通">
          <Toggle checked={states.college} onChange={toggle('college')} label="学院与班级消息" />
        </SettingRow>
        <SettingRow title="课程调整和作业提醒" description="调课、课程任务和截止时间">
          <Toggle checked={states.course} onChange={toggle('course')} label="课程提醒" />
        </SettingRow>
        <SettingRow title="校园事务进度" description="请假、证明、申请和办理状态">
          <Toggle checked={states.affairs} onChange={toggle('affairs')} label="事务进度" />
        </SettingRow>
        <SettingRow title="协作空间动态" description="投票、群体沟通和结果确认">
          <Toggle checked={states.scenes} onChange={toggle('scenes')} label="协作动态" />
        </SettingRow>
        <SettingRow title="Agent 任务结果" description="自动任务完成、失败和等待确认">
          <Toggle checked={states.agent} onChange={toggle('agent')} label="Agent 任务结果" />
        </SettingRow>
      </section>
      <section className="settings-section">
        <header>
          <div>
            <span>免打扰</span>
            <h3>安静时间</h3>
          </div>
        </header>
        <SettingRow title="每日免打扰" description="非紧急消息将在结束后集中提醒">
          <button>23:00 — 07:30　修改</button>
        </SettingRow>
        <SettingRow title="短信提醒" description="仅用于账号安全和学校紧急通知">
          <select aria-label="短信提醒">
            <option>仅紧急事项</option>
            <option>完全关闭</option>
          </select>
        </SettingRow>
      </section>
    </>
  );
}

function PrivacyPanel() {
  const [personalize, setPersonalize] = useState(true);
  return (
    <>
      <PanelHeading
        eyebrow="隐私与记忆"
        title="知识、记忆与隐私"
        description="了解 Agent 使用了什么，也可以随时修改、撤回或删除。"
      />
      <div className="settings-boundary-note">
        <span>
          <SettingsIcon name="privacy" />
        </span>
        <div>
          <strong>私人数据不会因管理身份自动开放</strong>
          <p>
            教师和管理员不能直接读取个人 Agent 记忆；心理健康数据不用于未经同意的监控、评价或处分。
          </p>
        </div>
      </div>
      <section className="settings-section">
        <header>
          <div>
            <span>个人记忆</span>
            <h3>Agent 如何了解你</h3>
          </div>
          <Link href="/memory">打开知识库</Link>
        </header>
        <SettingRow title="用于个性化支持" description="允许 Agent 使用你已经确认的偏好和长期记忆">
          <Toggle checked={personalize} onChange={setPersonalize} label="用于个性化支持" />
        </SettingRow>
        <SettingRow title="已保存记忆" description="课程学习 12 项、校园生活 7 项、个人偏好 6 项">
          <button>查看与编辑</button>
        </SettingRow>
        <SettingRow title="心理支持保护区" description="独立加密存储，仅由你主动使用或明确授权">
          <b className="settings-safe-text">严格保护</b>
        </SettingRow>
      </section>
      <section className="settings-section">
        <header>
          <div>
            <span>数据权利</span>
            <h3>导出、清除与访问记录</h3>
          </div>
        </header>
        <SettingRow title="最近数据访问" description="查看谁、在什么用途下使用了哪类数据">
          <button>查看审计记录</button>
        </SettingRow>
        <SettingRow title="导出个人数据" description="生成可下载的个人数据与授权清单">
          <button>申请导出</button>
        </SettingRow>
        <SettingRow title="清除 Agent 记忆" description="不会删除学校依法保存的学籍或事务记录">
          <button className="is-danger">管理清除</button>
        </SettingRow>
      </section>
    </>
  );
}

const CONNECTIONS = [
  { icon: '课', name: '课程与成绩', scope: '仅查询 · 本人课程信息', time: '今天 09:12' },
  { icon: '图', name: '暨南大学图书馆', scope: '查询与预约 · 提交前确认', time: '昨天 18:30' },
  { icon: '舍', name: '宿舍服务', scope: '查询与草稿', time: '7 月 18 日' },
  { icon: '历', name: '个人日历', scope: '读取与写入 · 每次确认', time: '今天 08:02' },
  { icon: '邮', name: '暨南大学邮箱', scope: '读取摘要 · 不读取私人邮件', time: '今天 08:01' },
];
function ConnectionsPanel() {
  return (
    <>
      <PanelHeading
        eyebrow="权限与连接"
        title="权限与连接"
        description="校园服务按任务授权，Agent 无法自行扩大权限。"
      />
      <div className="settings-permission-legend">
        <span>
          <i className="is-query" />
          仅查询
        </span>
        <span>
          <i className="is-draft" />
          可生成草稿
        </span>
        <span>
          <i className="is-confirm" />
          确认后执行
        </span>
      </div>
      <section className="settings-section">
        <header>
          <div>
            <span>已连接服务</span>
            <h3>校园系统与个人工具</h3>
          </div>
          <button>＋ 添加连接</button>
        </header>
        {CONNECTIONS.map((item) => (
          <SettingRow
            key={item.name}
            title={item.name}
            description={`${item.scope} · 最近使用 ${item.time}`}
          >
            <span className="settings-connection-action">
              <b>{item.icon}</b>
              <button>管理</button>
            </span>
          </SettingRow>
        ))}
      </section>
      <section className="settings-section">
        <header>
          <div>
            <span>默认规则</span>
            <h3>外部操作边界</h3>
          </div>
        </header>
        <SettingRow title="写入、发送和提交" description="Agent 停留在最后一步，等待你检查内容">
          <b className="settings-safe-text">始终确认</b>
        </SettingRow>
      </section>
    </>
  );
}

function SecurityPanel() {
  return (
    <>
      <PanelHeading
        eyebrow="账号安全"
        title="账号与安全"
        description="管理登录验证、设备和异常活动提醒。"
      />
      <div className="settings-security-score">
        <span>良好</span>
        <div>
          <strong>账号保护完整</strong>
          <p>手机已验证，最近没有发现异常登录。</p>
        </div>
        <button>运行安全检查</button>
      </div>
      <section className="settings-section">
        <header>
          <div>
            <span>登录保护</span>
            <h3>密码与验证方式</h3>
          </div>
        </header>
        <SettingRow title="暨南大学统一身份密码" description="密码由学校统一身份系统管理">
          <button>前往修改</button>
        </SettingRow>
        <SettingRow title="绑定手机" description="138••••1906 · 已验证">
          <button>管理</button>
        </SettingRow>
        <SettingRow title="重要操作二次确认" description="使用手机验证涉及隐私和外部提交的操作">
          <b className="settings-safe-text">已开启</b>
        </SettingRow>
      </section>
      <section className="settings-section">
        <header>
          <div>
            <span>登录设备</span>
            <h3>最近使用的设备</h3>
          </div>
          <button className="is-danger">退出其他设备</button>
        </header>
        <SettingRow title="Chrome · macOS" description="当前设备 · 广州 · 刚刚">
          <b className="settings-safe-text">当前</b>
        </SettingRow>
        <SettingRow title="CampusAgent · iPhone" description="广州 · 昨天 21:06">
          <button>移除</button>
        </SettingRow>
      </section>
    </>
  );
}

function AppearancePanel() {
  const [theme, setTheme] = useState('system');
  const [scale, setScale] = useState('comfortable');
  const [motion, setMotion] = useState(false);
  return (
    <>
      <PanelHeading
        eyebrow="显示与辅助功能"
        title="显示与辅助功能"
        description="调整主题、字号和动态效果，设置仅影响你的设备。"
      />
      <section className="settings-section">
        <header>
          <div>
            <span>显示</span>
            <h3>界面外观</h3>
          </div>
        </header>
        <SettingRow title="主题" description="当前界面跟随设备的外观设置">
          <div className="settings-segmented" aria-label="主题选择">
            {[
              ['light', '浅色'],
              ['dark', '深色'],
              ['system', '跟随系统'],
            ].map(([value, label]) => (
              <button
                key={value}
                className={theme === value ? 'is-active' : ''}
                onClick={() => setTheme(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </SettingRow>
        <SettingRow title="界面字号" description="所有功能页使用统一的可读字号">
          <div className="settings-segmented" aria-label="字号选择">
            {[
              ['compact', '标准'],
              ['comfortable', '舒适'],
              ['large', '较大'],
            ].map(([value, label]) => (
              <button
                key={value}
                className={scale === value ? 'is-active' : ''}
                onClick={() => setScale(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </SettingRow>
        <SettingRow title="减少动态效果" description="降低页面切换和状态变化时的动画">
          <Toggle checked={motion} onChange={setMotion} label="减少动态效果" />
        </SettingRow>
      </section>
      <section className="settings-section">
        <header>
          <div>
            <span>操作</span>
            <h3>键盘与语言</h3>
          </div>
        </header>
        <SettingRow title="快捷键" description="⌘ K 搜索，⌘ / 打开 Agent，⌘ ⇧ N 新建任务">
          <button>查看全部</button>
        </SettingRow>
        <SettingRow title="界面语言" description="CampusAgent 的菜单、提示和帮助语言">
          <select aria-label="界面语言">
            <option>简体中文</option>
            <option>English</option>
          </select>
        </SettingRow>
      </section>
    </>
  );
}

function HelpPanel() {
  return (
    <>
      <PanelHeading
        eyebrow="帮助与关于"
        title="帮助与关于"
        description="查找使用指南、联系支持并了解平台责任边界。"
      />
      <div className="settings-help-grid">
        <button>
          <span>
            <SettingsIcon name="overview" />
          </span>
          <strong>使用指南</strong>
          <p>了解 Agent、校园事务与协作空间</p>
        </button>
        <button>
          <span>
            <SettingsIcon name="help" />
          </span>
          <strong>联系校园支持</strong>
          <p>报告账号、连接或校园服务问题</p>
        </button>
        <button>
          <span>
            <SettingsIcon name="notifications" />
          </span>
          <strong>提交功能建议</strong>
          <p>帮助 CampusAgent 持续改进</p>
        </button>
      </div>
      <section className="settings-section">
        <header>
          <div>
            <span>关于平台</span>
            <h3>CampusAgent 暨南大学版</h3>
          </div>
          <em>v0.1.0</em>
        </header>
        <SettingRow title="服务运行状态" description="身份、消息、Agent 与校园连接运行正常">
          <b className="settings-live">
            <i />
            全部正常
          </b>
        </SettingRow>
        <SettingRow title="隐私政策与用户协议" description="了解数据用途、保存期限和你的权利">
          <button>查看文件</button>
        </SettingRow>
        <SettingRow
          title="人的最终判断"
          description="Agent 提供建议和协助，重要决策由相应责任人确认"
        >
          <b>平台基本原则</b>
        </SettingRow>
      </section>
    </>
  );
}

function GovernancePanel() {
  return (
    <>
      <PanelHeading
        eyebrow="学校系统治理"
        title="系统治理"
        description="学校管理员配置组织、规则、资源和服务，不管理学生的私人思想。"
      />
      <div className="settings-boundary-note is-admin">
        <span>
          <SettingsIcon name="governance" />
        </span>
        <div>
          <strong>管理权限不等于私人数据访问权</strong>
          <p>
            个人 Agent
            记忆、心理健康信息和行政管理数据保持分域，任何例外访问都需要合法依据、明确授权并全程审计。
          </p>
        </div>
      </div>
      <div className="settings-governance-grid">
        {[
          ['组织与角色', '组织架构、角色和职责边界'],
          ['服务与资源', '校园服务、Skills 和系统连接'],
          ['Agent 能力审批', '高风险工具与能力启用流程'],
          ['安全与审计', '访问记录、数据保留和风险策略'],
        ].map(([title, description]) => (
          <Link href="/admin" key={title}>
            <span>
              <SettingsIcon name="governance" />
            </span>
            <strong>{title}</strong>
            <p>{description}</p>
            <i>→</i>
          </Link>
        ))}
      </div>
    </>
  );
}

function SettingsContent() {
  const { user } = useAuth();
  const isAdmin = useIsAdmin();
  const [view, setView] = useState<SettingsView>('overview');
  const displayName = user?.display_name ?? '同学';
  const email = user?.email ?? '2024100123@stu.jnu.edu.cn';
  const navItems = useMemo(
    () => SETTING_NAV.filter((item) => !item.adminOnly || isAdmin),
    [isAdmin]
  );
  const active = navItems.find((item) => item.id === view) ?? navItems[0];
  return (
    <div className="settings-center">
      <header className="settings-hero">
        <div>
          <span>个人设置中心</span>
          <h1>设置与安全</h1>
          <p>管理校园身份、Agent 行为、消息提醒、个人数据与账号安全。</p>
        </div>
        <div className="settings-hero-status">
          <i />
          <span>
            <small>当前状态</small>
            <strong>设置已同步</strong>
          </span>
        </div>
      </header>
      <div className="settings-layout">
        <aside className="settings-nav" aria-label="设置分类">
          <div>
            <span>设置</span>
            <strong>你的 CampusAgent</strong>
            <small>更改将同步到当前账号</small>
          </div>
          <nav>
            {navItems.map((item) => (
              <button
                key={item.id}
                className={view === item.id ? 'is-active' : ''}
                onClick={() => setView(item.id)}
                aria-current={view === item.id ? 'page' : undefined}
              >
                <span>
                  <SettingsIcon name={item.icon} />
                </span>
                <p>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </p>
                <i>›</i>
              </button>
            ))}
          </nav>
        </aside>
        <main className="settings-content" aria-label={active.label}>
          {view === 'overview' && <OverviewPanel displayName={displayName} onNavigate={setView} />}
          {view === 'account' && <AccountPanel displayName={displayName} email={email} />}
          {view === 'agent' && <AgentPanel />}
          {view === 'notifications' && <NotificationsPanel />}
          {view === 'privacy' && <PrivacyPanel />}
          {view === 'connections' && <ConnectionsPanel />}
          {view === 'security' && <SecurityPanel />}
          {view === 'appearance' && <AppearancePanel />}
          {view === 'help' && <HelpPanel />}
          {view === 'governance' && isAdmin && <GovernancePanel />}
        </main>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <AppShell requireAuth>
      <SettingsContent />
    </AppShell>
  );
}
