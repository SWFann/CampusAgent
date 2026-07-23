'use client';

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { AppShell } from '@/components/app/AppShell';
import { useAuth } from '@/lib/auth';

type KnowledgeView =
  | 'home'
  | 'library'
  | 'courses'
  | 'campus'
  | 'materials'
  | 'preferences'
  | 'memories'
  | 'confirm'
  | 'wellbeing'
  | 'access'
  | 'archive';
type AddSource = 'upload' | 'note' | 'link' | 'conversation' | 'campus' | 'space';

interface KnowledgeItem {
  id: number;
  mark: string;
  title: string;
  summary: string;
  category: string;
  source: string;
  updated: string;
  agents: string;
  tone: string;
  dynamic?: boolean;
}

const KNOWLEDGE_ITEMS: KnowledgeItem[] = [
  {
    id: 1,
    mark: '软',
    title: '软件工程课程资料',
    summary: '课程要求、项目计划、作业规范与参考资料',
    category: '课程与学习',
    source: '本人上传 · 6 个文件',
    updated: '今天 09:20',
    agents: '课程 Agent',
    tone: 'green',
  },
  {
    id: 2,
    mark: '习',
    title: '我的学习方式',
    summary: '先梳理目标和截止时间，再按优先级制定计划',
    category: '偏好与规则',
    source: '本人确认',
    updated: '昨天',
    agents: '个人 Agent',
    tone: 'purple',
  },
  {
    id: 3,
    mark: '历',
    title: '本学期课程与日程',
    summary: '使用时从教务系统与个人日历读取最新信息',
    category: '课程与学习',
    source: '教务系统 · 动态连接',
    updated: '实时更新',
    agents: '个人、课程 Agent',
    tone: 'blue',
    dynamic: true,
  },
  {
    id: 4,
    mark: '申',
    title: '常用申请信息',
    summary: '个人申请中反复使用的基础信息和填写习惯',
    category: '事务与材料',
    source: '本人创建',
    updated: '7 月 18 日',
    agents: '事务 Agent',
    tone: 'amber',
  },
  {
    id: 5,
    mark: '协',
    title: '协作表达偏好',
    summary: '先展示共同点，再陈列差异与尚未确认的问题',
    category: '偏好与规则',
    source: '本人确认',
    updated: '7 月 16 日',
    agents: '协作 Agent',
    tone: 'purple',
  },
  {
    id: 6,
    mark: '校',
    title: '常用校园服务',
    summary: '石牌校区、图书馆与常用事务办理入口',
    category: '校园生活',
    source: '个人工作台整理',
    updated: '7 月 15 日',
    agents: '个人 Agent',
    tone: 'green',
  },
];

const NAV_ITEMS: Array<{
  id: KnowledgeView;
  label: string;
  description?: string;
  mark: string;
  badge?: string;
  divided?: boolean;
}> = [
  { id: 'home', label: '知识首页', description: '概览与最近更新', mark: '⌂' },
  { id: 'library', label: '全部知识', description: '资料、笔记与连接', mark: '知', badge: '36' },
  { id: 'courses', label: '课程与学习', mark: '课', badge: '12' },
  { id: 'campus', label: '校园生活', mark: '校', badge: '7' },
  { id: 'materials', label: '事务与材料', mark: '件', badge: '5' },
  { id: 'preferences', label: '偏好与规则', mark: '则', badge: '6' },
  {
    id: 'memories',
    label: 'Agent 记忆',
    description: '经过确认的长期记忆',
    mark: '忆',
    badge: '6',
    divided: true,
  },
  { id: 'confirm', label: '待我确认', description: 'Agent 建议的新记忆', mark: '待', badge: '2' },
  {
    id: 'wellbeing',
    label: '身心关怀',
    description: '自评与专业支持',
    mark: '心',
    badge: '受保护',
    divided: true,
  },
  { id: 'access', label: '授权与访问', description: '使用范围与记录', mark: '盾' },
  { id: 'archive', label: '归档与回收站', mark: '归' },
];

function KnowledgeIcon({ children }: { children: ReactNode }) {
  return (
    <span className="knowledge-mark" aria-hidden="true">
      {children}
    </span>
  );
}

function HomePanel({
  onAdd,
  onNavigate,
}: {
  onAdd: () => void;
  onNavigate: (view: KnowledgeView) => void;
}) {
  const [confirmed, setConfirmed] = useState(false);
  return (
    <>
      <div className="knowledge-heading">
        <div>
          <span>知识首页</span>
          <h2>让 Agent 更准确地理解你</h2>
          <p>知识来自你主动提供、确认的记忆和已授权的校园连接，每一项都可以追溯与撤回。</p>
        </div>
        <button className="knowledge-primary" onClick={onAdd}>
          ＋ 添加知识
        </button>
      </div>

      <section className="knowledge-readiness">
        <div className="knowledge-readiness-score">
          <span>
            <b>72</b>
            <small>%</small>
          </span>
          <div>
            <small>AGENT 知识准备度</small>
            <strong>已经可以支持大部分校园任务</strong>
            <p>补充常用事务材料，可以进一步减少重复填写。</p>
          </div>
        </div>
        <div className="knowledge-readiness-bars">
          <div>
            <span>课程学习</span>
            <i>
              <b style={{ width: '88%' }} />
            </i>
            <em>完善</em>
          </div>
          <div>
            <span>校园事务</span>
            <i>
              <b style={{ width: '54%' }} />
            </i>
            <em>基础</em>
          </div>
          <div>
            <span>个人偏好</span>
            <i>
              <b style={{ width: '82%' }} />
            </i>
            <em>完善</em>
          </div>
          <div>
            <span>常用材料</span>
            <i>
              <b style={{ width: '36%' }} />
            </i>
            <em>待补充</em>
          </div>
        </div>
      </section>

      {!confirmed && (
        <section className="knowledge-suggestion">
          <header>
            <KnowledgeIcon>忆</KnowledgeIcon>
            <div>
              <span>AGENT 建议记住</span>
              <h3>你希望在课程任务截止前一天收到提醒</h3>
            </div>
            <em>等待确认</em>
          </header>
          <p>依据：你最近三次都要求提前一天提醒。保存后，课程 Agent 会据此调整提醒时间。</p>
          <div>
            <span>使用范围 · 个人 Agent、课程 Agent</span>
            <button onClick={() => setConfirmed(true)}>允许记住</button>
            <button>修改后保存</button>
            <button onClick={() => setConfirmed(true)}>不用记住</button>
          </div>
        </section>
      )}
      {confirmed && (
        <div className="knowledge-confirmed-note">
          <span>✓</span>
          <p>
            <strong>已处理这条记忆建议</strong>
            <small>你可以随时在“Agent 记忆”中修改或撤回。</small>
          </p>
        </div>
      )}

      <section className="knowledge-section">
        <header>
          <div>
            <span>最近更新</span>
            <h3>Agent 可以使用的知识</h3>
          </div>
          <button onClick={() => onNavigate('library')}>
            查看全部 <i>→</i>
          </button>
        </header>
        <div className="knowledge-recent-grid">
          {KNOWLEDGE_ITEMS.slice(0, 4).map((item) => (
            <article key={item.id}>
              <KnowledgeIcon>
                <span className={`is-${item.tone}`}>{item.mark}</span>
              </KnowledgeIcon>
              <div>
                <span>
                  {item.category}
                  {item.dynamic && <em>动态</em>}
                </span>
                <strong>{item.title}</strong>
                <p>{item.summary}</p>
              </div>
              <footer>
                <span>{item.source}</span>
                <button aria-label={`查看${item.title}`}>›</button>
              </footer>
            </article>
          ))}
        </div>
      </section>

      <div className="knowledge-home-columns">
        <section className="knowledge-section">
          <header>
            <div>
              <span>知识分类</span>
              <h3>按校园场景组织</h3>
            </div>
          </header>
          <div className="knowledge-category-list">
            <button onClick={() => onNavigate('courses')}>
              <span className="is-green">课</span>
              <p>
                <strong>课程与学习</strong>
                <small>课程资料、笔记与学习计划</small>
              </p>
              <em>12</em>
            </button>
            <button onClick={() => onNavigate('campus')}>
              <span className="is-blue">校</span>
              <p>
                <strong>校园生活</strong>
                <small>常用校区、服务与活动</small>
              </p>
              <em>7</em>
            </button>
            <button onClick={() => onNavigate('materials')}>
              <span className="is-amber">件</span>
              <p>
                <strong>事务与材料</strong>
                <small>申请信息、模板与证明材料</small>
              </p>
              <em>5</em>
            </button>
            <button onClick={() => onNavigate('preferences')}>
              <span className="is-purple">则</span>
              <p>
                <strong>偏好与规则</strong>
                <small>表达方式、提醒习惯与边界</small>
              </p>
              <em>6</em>
            </button>
          </div>
        </section>
        <section className="knowledge-section">
          <header>
            <div>
              <span>最近使用</span>
              <h3>知识如何增强了 Agent</h3>
            </div>
            <button onClick={() => onNavigate('access')}>访问记录</button>
          </header>
          <div className="knowledge-usage-list">
            <article>
              <time>09:12</time>
              <span className="is-green">课</span>
              <p>
                <strong>课程 Agent 使用了“本学期课程信息”</strong>
                <small>用途：生成今日校园简报 · 仅本人可见</small>
              </p>
            </article>
            <article>
              <time>昨天</time>
              <span className="is-amber">申</span>
              <p>
                <strong>事务 Agent 使用了“常用申请信息”</strong>
                <small>用途：准备请假申请草稿 · 尚未提交</small>
              </p>
            </article>
            <article>
              <time>周三</time>
              <span className="is-purple">协</span>
              <p>
                <strong>协作 Agent 使用了“表达偏好”</strong>
                <small>用途：整理宿舍协作中的共同意见</small>
              </p>
            </article>
          </div>
        </section>
      </div>
    </>
  );
}

function LibraryPanel({ view, onAdd }: { view: KnowledgeView; onAdd: () => void }) {
  const [query, setQuery] = useState('');
  const headingMap: Partial<Record<KnowledgeView, [string, string]>> = {
    library: ['全部知识', '集中管理资料、笔记、规则和校园动态连接'],
    courses: ['课程与学习', '帮助 Agent 理解课程背景、学习资料和个人计划'],
    campus: ['校园生活', '常用校区、校园服务、社团与活动信息'],
    materials: ['事务与材料', '申请信息、常用模板和个人办理材料'],
    preferences: ['偏好与规则', '告诉 Agent 如何与你配合，以及哪些边界不可越过'],
  };
  const [title, description] = headingMap[view] ?? headingMap.library!;
  const categoryMap: Partial<Record<KnowledgeView, string>> = {
    courses: '课程与学习',
    campus: '校园生活',
    materials: '事务与材料',
    preferences: '偏好与规则',
  };
  const visible = KNOWLEDGE_ITEMS.filter(
    (item) =>
      (!categoryMap[view] || item.category === categoryMap[view]) &&
      (!query || `${item.title}${item.summary}${item.category}`.includes(query))
  );
  return (
    <>
      <div className="knowledge-heading">
        <div>
          <span>我的知识库</span>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <button className="knowledge-primary" onClick={onAdd}>
          ＋ 添加知识
        </button>
      </div>
      <div className="knowledge-toolbar">
        <div>
          <button className="is-active">全部</button>
          <button>文档</button>
          <button>笔记</button>
          <button>动态连接</button>
        </div>
        <label>
          <span>⌕</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="搜索个人知识库"
            placeholder="搜索知识、来源或标签"
          />
        </label>
        <button aria-label="切换列表布局">☷</button>
      </div>
      <div className="knowledge-table" role="table" aria-label={`${title}列表`}>
        <header role="row">
          <span>知识名称</span>
          <span>来源与更新时间</span>
          <span>可使用的 Agent</span>
          <span>状态</span>
          <span />
        </header>
        {visible.map((item) => (
          <article role="row" key={item.id}>
            <div>
              <KnowledgeIcon>
                <span className={`is-${item.tone}`}>{item.mark}</span>
              </KnowledgeIcon>
              <p>
                <strong>{item.title}</strong>
                <small>{item.summary}</small>
              </p>
            </div>
            <div>
              <strong>{item.source}</strong>
              <small>{item.updated}</small>
            </div>
            <span>{item.agents}</span>
            <em className={item.dynamic ? 'is-dynamic' : ''}>
              {item.dynamic ? '实时连接' : '可用'}
            </em>
            <button aria-label={`更多${item.title}操作`}>•••</button>
          </article>
        ))}
        {visible.length === 0 && (
          <div className="knowledge-empty">
            <span>⌕</span>
            <strong>没有找到相关知识</strong>
            <p>尝试更换关键词，或者添加一项新知识。</p>
          </div>
        )}
      </div>
      <div className="knowledge-dynamic-note">
        <span>连</span>
        <p>
          <strong>校园权威数据采用动态连接</strong>
          <small>课表、成绩和办理进度不会复制成长期记忆，Agent 使用时读取最新结果。</small>
        </p>
        <button>管理校园连接</button>
      </div>
    </>
  );
}

function MemoriesPanel({ confirmOnly = false }: { confirmOnly?: boolean }) {
  const [items, setItems] = useState(
    [
      {
        id: 1,
        text: '课程任务通常提前一天提醒',
        evidence: '最近 3 次个人工作台对话',
        agents: '个人、课程 Agent',
        state: confirmOnly ? 'pending' : 'saved',
      },
      {
        id: 2,
        text: '回答校园事务时先给出办理入口和材料清单',
        evidence: '由你在偏好设置中创建',
        agents: '个人、事务 Agent',
        state: confirmOnly ? 'pending' : 'saved',
      },
      {
        id: 3,
        text: '常用石牌校区的图书馆和校园服务',
        evidence: '本人于 7 月 15 日确认',
        agents: '个人 Agent',
        state: 'saved',
      },
    ].filter((item) => !confirmOnly || item.state === 'pending')
  );
  const remove = (id: number) => setItems((current) => current.filter((item) => item.id !== id));
  return (
    <>
      <div className="knowledge-heading">
        <div>
          <span>{confirmOnly ? '记忆确认队列' : 'Agent 记忆'}</span>
          <h2>{confirmOnly ? '待我确认' : 'Agent 记忆'}</h2>
          <p>
            {confirmOnly
              ? 'Agent 只能提出记忆建议，由你决定是否保存。'
              : '经过你确认的长期记忆，可以修改、停用或设置使用范围。'}
          </p>
        </div>
        {!confirmOnly && <button>＋ 创建记忆</button>}
      </div>
      {confirmOnly && (
        <div className="knowledge-review-intro">
          <span>2</span>
          <p>
            <strong>有 2 条新的记忆建议</strong>
            <small>敏感信息不会在这里自动形成记忆，未确认内容也不会用于后续任务。</small>
          </p>
        </div>
      )}
      <div className="knowledge-memory-list">
        {items.map((item) => (
          <article key={item.id}>
            <header>
              <span className={confirmOnly ? 'is-pending' : ''}>忆</span>
              <div>
                <small>{confirmOnly ? 'AGENT 建议记住' : '长期记忆'}</small>
                <strong>{item.text}</strong>
              </div>
              <em>{confirmOnly ? '等待确认' : '使用中'}</em>
            </header>
            <dl>
              <div>
                <dt>形成依据</dt>
                <dd>{item.evidence}</dd>
              </div>
              <div>
                <dt>使用范围</dt>
                <dd>{item.agents}</dd>
              </div>
              <div>
                <dt>敏感等级</dt>
                <dd>普通</dd>
              </div>
            </dl>
            <footer>
              {confirmOnly ? (
                <>
                  <button className="is-primary" onClick={() => remove(item.id)}>
                    允许记住
                  </button>
                  <button>修改后保存</button>
                  <button onClick={() => remove(item.id)}>不用记住</button>
                </>
              ) : (
                <>
                  <span>最近使用 · 今天 09:12</span>
                  <button>修改</button>
                  <button>暂停使用</button>
                </>
              )}
            </footer>
          </article>
        ))}
        {items.length === 0 && (
          <div className="knowledge-empty">
            <span>✓</span>
            <strong>已经全部处理完成</strong>
            <p>新的记忆建议会显示在这里。</p>
          </div>
        )}
      </div>
    </>
  );
}

function AccessPanel() {
  return (
    <>
      <div className="knowledge-heading">
        <div>
          <span>授权与隐私</span>
          <h2>授权与访问</h2>
          <p>查看哪些 Agent 可以使用你的知识，以及每次使用的原因和结果。</p>
        </div>
        <button>导出访问记录</button>
      </div>
      <div className="knowledge-access-summary">
        <article>
          <span className="is-green">18</span>
          <p>
            <strong>可供 Agent 使用</strong>
            <small>所有范围均由你授权</small>
          </p>
        </article>
        <article>
          <span className="is-blue">4</span>
          <p>
            <strong>动态校园连接</strong>
            <small>使用时读取，不复制数据</small>
          </p>
        </article>
        <article>
          <span className="is-amber">3</span>
          <p>
            <strong>每次使用前确认</strong>
            <small>申请材料与身份信息</small>
          </p>
        </article>
      </div>
      <section className="knowledge-access-block">
        <header>
          <div>
            <span>最近访问</span>
            <h3>知识使用记录</h3>
          </div>
          <div>
            <button className="is-active">全部</button>
            <button>个人 Agent</button>
            <button>专项 Agent</button>
          </div>
        </header>
        <div className="knowledge-access-timeline">
          <article>
            <time>
              今天
              <br />
              <strong>09:12</strong>
            </time>
            <span className="is-green">课</span>
            <p>
              <strong>课程 Agent 读取“本学期课程与日程”</strong>
              <small>用途：生成今日校园简报 · 来源：教务系统动态连接</small>
            </p>
            <em>读取成功</em>
            <button>详情</button>
          </article>
          <article>
            <time>
              昨天
              <br />
              <strong>20:18</strong>
            </time>
            <span className="is-amber">申</span>
            <p>
              <strong>事务 Agent 使用“常用申请信息”</strong>
              <small>用途：准备请假申请草稿 · 未发生外部提交</small>
            </p>
            <em>本人已确认</em>
            <button>详情</button>
          </article>
          <article>
            <time>
              周三
              <br />
              <strong>18:40</strong>
            </time>
            <span className="is-purple">协</span>
            <p>
              <strong>协作 Agent 读取“协作表达偏好”</strong>
              <small>用途：整理宿舍聚餐协作的公开意见</small>
            </p>
            <em>读取成功</em>
            <button>详情</button>
          </article>
        </div>
      </section>
      <div className="knowledge-protected">
        <span>护</span>
        <div>
          <strong>受保护信息不会进入普通知识检索</strong>
          <p>
            心理健康、医疗和其他高度敏感信息严格分域，仅在你主动进入对应支持场景时使用，教师与管理员不能因身份直接访问。
          </p>
        </div>
        <button>查看保护规则</button>
      </div>
    </>
  );
}

const WELLBEING_QUESTIONS = [
  '我感到心情愉快、精神很好',
  '我感到宁静和放松',
  '我感到充满活力、精力充沛',
  '我睡醒时感到清新，得到了足够休息',
  '我的日常生活中充满令我感兴趣的事情',
];

const WELLBEING_OPTIONS = [
  { label: '所有时间', score: 5 },
  { label: '大部分时间', score: 4 },
  { label: '超过一半时间', score: 3 },
  { label: '少于一半时间', score: 2 },
  { label: '偶尔', score: 1 },
  { label: '从未', score: 0 },
];

function WellbeingPanel() {
  const [started, setStarted] = useState(false);
  const [answers, setAnswers] = useState<Array<number | null>>(() =>
    WELLBEING_QUESTIONS.map(() => null)
  );
  const [result, setResult] = useState<number | null>(null);
  const [saveResult, setSaveResult] = useState(false);
  const [reminder, setReminder] = useState(false);
  const answeredCount = answers.filter((answer) => answer !== null).length;
  const submit = () => {
    if (answeredCount !== WELLBEING_QUESTIONS.length) return;
    setResult(answers.reduce<number>((total, answer) => total + (answer ?? 0), 0) * 4);
  };
  const restart = () => {
    setAnswers(WELLBEING_QUESTIONS.map(() => null));
    setResult(null);
    setStarted(true);
  };

  return (
    <>
      <div className="knowledge-heading wellbeing-heading">
        <div>
          <span>个人身心关怀</span>
          <h2>身心关怀</h2>
          <p>
            了解自己最近的状态，在需要时更容易找到支持。这里不是诊断，也不会成为学校评价你的工具。
          </p>
        </div>
        <span className="wellbeing-protected-badge">受保护空间</span>
      </div>

      <section className="wellbeing-privacy-banner">
        <span>盾</span>
        <div>
          <strong>结果默认只在本次页面显示</strong>
          <p>
            不自动保存、不进入普通 Agent
            记忆，也不会提供给教师、辅导员或管理员。只有你主动选择时，才会保存到受保护空间。
          </p>
        </div>
        <button>查看隐私说明</button>
      </section>

      {!started && result === null && (
        <>
          <section className="wellbeing-intro-card">
            <div>
              <span>WHO-5</span>
              <small>世界卫生组织五项身心健康指标</small>
            </div>
            <h3>过去两周，你的整体状态怎么样？</h3>
            <p>
              通过 5 个简短问题了解近期主观福祉。完成大约需要 1
              分钟，结果仅用于自我了解和是否寻求进一步支持的参考。
            </p>
            <dl>
              <div>
                <dt>问题数量</dt>
                <dd>5 项</dd>
              </div>
              <div>
                <dt>回顾时间</dt>
                <dd>过去两周</dd>
              </div>
              <div>
                <dt>结果性质</dt>
                <dd>自评参考</dd>
              </div>
            </dl>
            <button onClick={() => setStarted(true)}>
              开始自评 <span>→</span>
            </button>
            <a
              href="https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01"
              target="_blank"
              rel="noreferrer"
            >
              查看 WHO-5 官方说明
            </a>
          </section>
          <div className="wellbeing-support-grid">
            <article>
              <span className="is-green">聊</span>
              <div>
                <strong>想找人聊一聊</strong>
                <p>可以主动预约暨南大学心理健康教育中心的专业服务。</p>
              </div>
              <a href="https://www.jnu.edu.cn/36423/main.htm" target="_blank" rel="noreferrer">
                查看校内服务
              </a>
            </article>
            <article>
              <span className="is-blue">记</span>
              <div>
                <strong>日常状态记录</strong>
                <p>只记录你愿意保留的感受，用来观察自己的变化。</p>
              </div>
              <button onClick={() => setReminder((value) => !value)}>
                {reminder ? '已开启提醒' : '设置自评提醒'}
              </button>
            </article>
          </div>
        </>
      )}

      {started && result === null && (
        <section className="wellbeing-assessment">
          <header>
            <div>
              <span>过去两周</span>
              <h3>请选择最符合你实际感受的答案</h3>
              <p>没有标准答案，可以跳出或稍后再做。</p>
            </div>
            <em>
              {answeredCount} / {WELLBEING_QUESTIONS.length}
            </em>
          </header>
          <div className="wellbeing-progress">
            <i style={{ width: `${(answeredCount / WELLBEING_QUESTIONS.length) * 100}%` }} />
          </div>
          <div className="wellbeing-question-list">
            {WELLBEING_QUESTIONS.map((question, questionIndex) => (
              <fieldset key={question}>
                <legend>
                  <span>{questionIndex + 1}</span>
                  {question}
                </legend>
                <div>
                  {WELLBEING_OPTIONS.map((option) => (
                    <label
                      key={option.score}
                      className={answers[questionIndex] === option.score ? 'is-selected' : ''}
                    >
                      <input
                        type="radio"
                        name={`wellbeing-${questionIndex}`}
                        value={option.score}
                        checked={answers[questionIndex] === option.score}
                        onChange={() =>
                          setAnswers((current) =>
                            current.map((answer, index) =>
                              index === questionIndex ? option.score : answer
                            )
                          )
                        }
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
          </div>
          <footer>
            <label>
              <input
                type="checkbox"
                checked={saveResult}
                onChange={(event) => setSaveResult(event.target.checked)}
              />
              <span>
                <strong>将本次结果保存到受保护空间</strong>
                <small>默认不保存；即使保存也不会进入普通 Agent 知识库。</small>
              </span>
            </label>
            <div>
              <button onClick={() => setStarted(false)}>暂时退出</button>
              <button
                className="is-primary"
                disabled={answeredCount !== WELLBEING_QUESTIONS.length}
                onClick={submit}
              >
                查看自评结果
              </button>
            </div>
          </footer>
        </section>
      )}

      {result !== null && (
        <section className={`wellbeing-result${result < 50 ? ' needs-support' : ''}`}>
          <header>
            <span>
              <b>{result}</b>
              <small>/ 100</small>
            </span>
            <div>
              <small>本次 WHO-5 自评结果</small>
              <h3>
                {result < 50 ? '最近可能有些辛苦，值得多给自己一些支持' : '近期整体状态相对平稳'}
              </h3>
              <p>
                {result < 50
                  ? '这个分数提示近期主观福祉感偏低，建议与专业人员进一步聊聊。它不是任何心理疾病的诊断。'
                  : '你可以把它作为一次状态记录；如果仍有困扰，也可以随时主动联系专业支持。'}
              </p>
            </div>
          </header>
          <div className="wellbeing-result-boundary">
            <span>重要说明</span>
            <p>
              自评结果不能替代专业评估。CampusAgent
              不会据此进行诊断、预警排名、学业评价或自动通知学校人员。
            </p>
          </div>
          <div className="wellbeing-result-actions">
            <button
              className="is-primary"
              onClick={() =>
                window.open(
                  'https://www.jnu.edu.cn/36423/main.htm',
                  '_blank',
                  'noopener,noreferrer'
                )
              }
            >
              联系校内心理服务
            </button>
            <button onClick={() => setReminder((value) => !value)}>
              {reminder ? '已设置两周后提醒' : '两周后提醒我再测'}
            </button>
            <button onClick={restart}>重新自评</button>
          </div>
          {saveResult && (
            <div className="wellbeing-saved">
              <span>✓</span>
              <p>
                <strong>已选择保存到受保护空间</strong>
                <small>这里只保存分数和日期，不保存每一道题的具体选择。你可以随时删除。</small>
              </p>
            </div>
          )}
        </section>
      )}

      <section className="wellbeing-help-card">
        <div>
          <span>援</span>
          <p>
            <strong>如果你此刻感到难以承受，或者担心自己或他人的安全</strong>
            <small>请立即联系可信任的人、学校心理健康教育中心或当地紧急服务，不必独自面对。</small>
          </p>
        </div>
        <div>
          <a href="tel:12356">
            <strong>12356</strong>
            <span>全国心理援助热线</span>
          </a>
          <a href="tel:02085224200">
            <strong>020-85224200</strong>
            <span>暨南大学心理健康教育中心</span>
          </a>
        </div>
      </section>

      <section className="wellbeing-history">
        <header>
          <div>
            <span>我的记录</span>
            <h3>状态趋势</h3>
          </div>
          <label>
            <input
              type="checkbox"
              checked={reminder}
              onChange={(event) => setReminder(event.target.checked)}
            />
            <span>每两周提醒我主动自评</span>
          </label>
        </header>
        <div className="wellbeing-empty-history">
          <span>趋</span>
          <p>
            <strong>暂无已保存记录</strong>
            <small>只有你主动选择保存后，趋势才会显示在这里。</small>
          </p>
        </div>
      </section>
    </>
  );
}

function ArchivePanel() {
  return (
    <>
      <div className="knowledge-heading">
        <div>
          <span>归档管理</span>
          <h2>归档与回收站</h2>
          <p>停用的知识不会再被 Agent 检索；删除内容会在安全保留期后彻底清除。</p>
        </div>
      </div>
      <div className="knowledge-empty is-large">
        <span>归</span>
        <strong>当前没有归档内容</strong>
        <p>停用、过期或删除的知识会显示在这里。</p>
      </div>
    </>
  );
}

function AddKnowledgeDrawer({ onClose }: { onClose: () => void }) {
  const [source, setSource] = useState<AddSource | null>(null);
  const [step, setStep] = useState(1);
  const sources: Array<{ id: AddSource; mark: string; title: string; text: string }> = [
    { id: 'upload', mark: '文', title: '上传文件', text: 'PDF、Word、图片或文本资料' },
    { id: 'note', mark: '笔', title: '创建笔记', text: '直接写下背景、规则或个人说明' },
    { id: 'link', mark: '链', title: '网页链接', text: '保存网页并提取可用知识' },
    { id: 'conversation', mark: '话', title: '从对话整理', text: '从个人工作台选择一段对话' },
    { id: 'campus', mark: '校', title: '校园系统', text: '建立教务、日历等动态连接' },
    { id: 'space', mark: '协', title: '组织与空间', text: '引用课程或协作空间中的资料' },
  ];
  return (
    <div
      className="knowledge-drawer-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside
        className="knowledge-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-knowledge-title"
      >
        <header>
          <div>
            <span>添加知识</span>
            <h2 id="add-knowledge-title">添加到个人知识库</h2>
            <p>添加前，Agent 会先说明识别结果和需要的权限。</p>
          </div>
          <button onClick={onClose} aria-label="关闭添加知识面板">
            ×
          </button>
        </header>
        <div className="knowledge-drawer-progress">
          <span className="is-active" />
          <span className={step >= 2 ? 'is-active' : ''} />
          <span className={step >= 3 ? 'is-active' : ''} />
        </div>
        <div className="knowledge-drawer-content">
          {step === 1 && (
            <>
              <div className="knowledge-drawer-title">
                <span>01</span>
                <div>
                  <strong>选择知识来源</strong>
                  <p>你可以随时修改或撤回添加的内容。</p>
                </div>
              </div>
              <div className="knowledge-source-grid">
                {sources.map((item) => (
                  <button
                    key={item.id}
                    className={source === item.id ? 'is-selected' : ''}
                    onClick={() => setSource(item.id)}
                  >
                    <span>{item.mark}</span>
                    <div>
                      <strong>{item.title}</strong>
                      <small>{item.text}</small>
                    </div>
                    <i>✓</i>
                  </button>
                ))}
              </div>
            </>
          )}
          {step === 2 && (
            <>
              <div className="knowledge-drawer-title">
                <span>02</span>
                <div>
                  <strong>补充知识信息</strong>
                  <p>这是演示界面，不会上传真实文件。</p>
                </div>
              </div>
              <div className="knowledge-add-form">
                <label>
                  <span>知识名称</span>
                  <input defaultValue={source === 'campus' ? '我的校园动态连接' : '新的个人知识'} />
                </label>
                <label>
                  <span>分类</span>
                  <select defaultValue="课程与学习">
                    <option>课程与学习</option>
                    <option>校园生活</option>
                    <option>事务与材料</option>
                    <option>偏好与规则</option>
                  </select>
                </label>
                <label>
                  <span>内容或说明</span>
                  <textarea rows={5} placeholder="输入希望 Agent 理解的信息，或在这里放置文件…" />
                </label>
              </div>
              <div className="knowledge-analysis-tip">
                <span>AI</span>
                <p>
                  <strong>保存前会先生成理解预览</strong>
                  <small>
                    Agent 会识别主题、可能的敏感信息和建议使用范围，不会直接写入长期记忆。
                  </small>
                </p>
              </div>
            </>
          )}
          {step === 3 && (
            <>
              <div className="knowledge-drawer-title">
                <span>03</span>
                <div>
                  <strong>设置 Agent 使用范围</strong>
                  <p>默认仅供你的个人 Agent 使用。</p>
                </div>
              </div>
              <div className="knowledge-permission-options">
                <label>
                  <input type="checkbox" defaultChecked />
                  <span>
                    <strong>个人 Agent</strong>
                    <small>在个人工作台查询和整理</small>
                  </span>
                </label>
                <label>
                  <input type="checkbox" />
                  <span>
                    <strong>课程 Agent</strong>
                    <small>用于课程计划和资料整理</small>
                  </span>
                </label>
                <label>
                  <input type="checkbox" />
                  <span>
                    <strong>校园事务 Agent</strong>
                    <small>用于准备事务材料，提交前仍需确认</small>
                  </span>
                </label>
                <label>
                  <input type="checkbox" />
                  <span>
                    <strong>协作 Agent</strong>
                    <small>仅允许使用你明确共享的内容</small>
                  </span>
                </label>
              </div>
              <div className="knowledge-safety-check">
                <span>盾</span>
                <p>
                  <strong>安全检查通过</strong>
                  <small>未发现需要单独分域的敏感信息。你仍可在保存后修改授权。</small>
                </p>
              </div>
            </>
          )}
        </div>
        <footer>
          <button onClick={step === 1 ? onClose : () => setStep((value) => value - 1)}>
            {step === 1 ? '取消' : '上一步'}
          </button>
          {step < 3 ? (
            <button
              className="is-primary"
              disabled={!source}
              onClick={() => setStep((value) => value + 1)}
            >
              继续
            </button>
          ) : (
            <button className="is-primary" onClick={onClose}>
              确认添加
            </button>
          )}
        </footer>
      </aside>
    </div>
  );
}

function KnowledgeContent() {
  const { user } = useAuth();
  const [view, setView] = useState<KnowledgeView>('home');
  const [showAdd, setShowAdd] = useState(false);
  const contentRef = useRef<HTMLElement>(null);
  const displayName = user?.display_name ?? '同学';
  const currentLabel = useMemo(
    () => NAV_ITEMS.find((item) => item.id === view)?.label ?? '知识首页',
    [view]
  );
  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0, behavior: 'instant' });
  }, [view]);
  return (
    <div className="knowledge-center">
      <header className="knowledge-hero">
        <div className="knowledge-hero-copy">
          <span className="knowledge-hero-icon">
            知<i />
          </span>
          <div>
            <span>我的个人知识库</span>
            <h1>{displayName}的知识空间</h1>
            <p>让 Agent 在你允许的范围内，更准确地理解你的学习、校园生活和个人需求。</p>
          </div>
        </div>
        <div className="knowledge-hero-stats">
          <div>
            <strong>36</strong>
            <span>知识条目</span>
          </div>
          <div>
            <strong>18</strong>
            <span>Agent 可用</span>
          </div>
          <div>
            <strong>12</strong>
            <span>本周使用</span>
          </div>
        </div>
        <button onClick={() => setShowAdd(true)}>＋ 添加知识</button>
      </header>
      <div className="knowledge-layout">
        <aside className="knowledge-nav" aria-label="个人知识库导航">
          <div>
            <span>个人知识库</span>
            <strong>我的知识</strong>
            <small>知识由你提供、确认和控制</small>
          </div>
          <nav>
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                className={`${view === item.id ? 'is-active' : ''}${item.divided ? ' is-divided' : ''}`}
                onClick={() => setView(item.id)}
                aria-current={view === item.id ? 'page' : undefined}
              >
                <KnowledgeIcon>{item.mark}</KnowledgeIcon>
                <p>
                  <strong>{item.label}</strong>
                  {item.description && <small>{item.description}</small>}
                </p>
                {item.badge && <em>{item.badge}</em>}
              </button>
            ))}
          </nav>
          <div className="knowledge-nav-storage">
            <span>
              <i style={{ width: '28%' }} />
            </span>
            <p>
              <strong>个人空间 1.4 GB / 5 GB</strong>
              <small>文件原件与索引均加密存储</small>
            </p>
          </div>
        </aside>
        <main ref={contentRef} className="knowledge-content" aria-label={currentLabel}>
          {view === 'home' && <HomePanel onAdd={() => setShowAdd(true)} onNavigate={setView} />}
          {['library', 'courses', 'campus', 'materials', 'preferences'].includes(view) && (
            <LibraryPanel view={view} onAdd={() => setShowAdd(true)} />
          )}
          {view === 'memories' && <MemoriesPanel />}
          {view === 'confirm' && <MemoriesPanel confirmOnly />}
          {view === 'wellbeing' && <WellbeingPanel />}
          {view === 'access' && <AccessPanel />}
          {view === 'archive' && <ArchivePanel />}
        </main>
        <aside className="knowledge-inspector">
          <section className="knowledge-agent-card">
            <header>
              <span>CA</span>
              <div>
                <strong>Agent 知识状态</strong>
                <small>最近同步 · 2 分钟前</small>
              </div>
              <i>
                <b />
                正常
              </i>
            </header>
            <div className="knowledge-agent-score">
              <span>
                <b>72</b>%
              </span>
              <p>
                <strong>知识准备度</strong>
                <small>能够支持课程、通知与常用事务</small>
              </p>
            </div>
            <dl>
              <div>
                <dt>已启用知识</dt>
                <dd>18 项</dd>
              </div>
              <div>
                <dt>动态连接</dt>
                <dd>4 项</dd>
              </div>
              <div>
                <dt>待确认记忆</dt>
                <dd>2 项</dd>
              </div>
            </dl>
            <button onClick={() => setView('confirm')}>
              处理记忆建议 <span>→</span>
            </button>
          </section>
          <section className="knowledge-boundary">
            <header>
              <span>盾</span>
              <div>
                <strong>知识使用边界</strong>
                <small>适用于所有个人 Agent</small>
              </div>
            </header>
            <ul>
              <li>
                <i />
                只有授权的 Agent 可以检索
              </li>
              <li>
                <i />
                每次使用均记录来源和用途
              </li>
              <li>
                <i />
                敏感信息不进入普通知识检索
              </li>
              <li>
                <i />
                教师和管理员不能直接读取
              </li>
            </ul>
            <button onClick={() => setView('access')}>管理授权与访问</button>
          </section>
          <section className="knowledge-inspector-tip">
            <span>知识不等于监控</span>
            <p>Agent 可以利用知识提供支持，但不能据此进行未经同意的评价、诊断或处分。</p>
          </section>
        </aside>
      </div>
      {showAdd && <AddKnowledgeDrawer onClose={() => setShowAdd(false)} />}
    </div>
  );
}

export default function MemoryPage() {
  return (
    <AppShell requireAuth>
      <KnowledgeContent />
    </AppShell>
  );
}
