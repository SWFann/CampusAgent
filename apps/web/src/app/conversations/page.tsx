"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app/AppShell";
import {
  createGroupConversation,
  createPrivateConversation,
  listConversations,
  type ConversationListItem,
} from "@/lib/conversations";
import { listContacts, type ContactItem } from "@/lib/contacts";
import { searchDirectory, type DirectoryUserResult } from "@/lib/directory";
import { formatDate } from "@/lib/utils";

type NoticeCategory = "all" | "important" | "todo" | "unread" | "official" | "course" | "service" | "collaboration";

interface NoticeItem {
  id: string;
  category: Exclude<NoticeCategory, "all" | "important" | "todo" | "unread">;
  source: string;
  title: string;
  summary: string;
  original: string;
  time: string;
  priority: "urgent" | "important" | "normal";
  unread: boolean;
  actionable: boolean;
  status?: string;
  deadline?: string;
  audience: string;
  href: string;
  actionLabel: string;
  icon: string;
}

const DEMO_NOTICES: NoticeItem[] = [
  {
    id: "notice-scholarship",
    category: "official",
    source: "信息科学技术学院",
    title: "关于2026年度本科生奖学金申请的通知",
    summary: "符合条件的同学需在7月25日前提交申请表、成绩单与相关证明材料。",
    original: "学院现启动2026年度本科生奖学金申请工作。请有意申请且符合条件的同学，按要求准备申请表、成绩单及相关证明材料，并于规定时间前完成提交。",
    time: "今天 09:30",
    priority: "urgent",
    unread: true,
    actionable: true,
    status: "需要办理",
    deadline: "7月25日 18:00",
    audience: "信息学院本科生",
    href: "/organizations",
    actionLabel: "去办理",
    icon: "院",
  },
  {
    id: "notice-course-room",
    category: "course",
    source: "软件工程课程组",
    title: "周三《软件工程》课程地点调整",
    summary: "本周三课程由教学楼A204调整至番禺校区实验楼B307，上课时间不变。",
    original: "因教学设备维护，本周三《软件工程》课程上课地点调整为实验楼B307。上课时间及教学内容不变，请同学们相互转告。",
    time: "今天 08:45",
    priority: "important",
    unread: true,
    actionable: false,
    status: "课程调整",
    audience: "软件工程课程成员",
    href: "/organizations",
    actionLabel: "查看课程",
    icon: "课",
  },
  {
    id: "notice-leave-progress",
    category: "service",
    source: "学生事务服务中心",
    title: "你的请假申请已进入辅导员审核",
    summary: "申请材料已提交，当前无需补充材料，预计1个工作日内完成审核。",
    original: "你的请假申请已成功提交并进入辅导员审核环节。如需补充材料，系统将通过消息中心另行通知。",
    time: "昨天 16:20",
    priority: "normal",
    unread: false,
    actionable: true,
    status: "办理中",
    audience: "仅本人",
    href: "/organizations",
    actionLabel: "查看进度",
    icon: "办",
  },
];

const CATEGORY_ITEMS: Array<{ key: NoticeCategory; label: string; icon: string }> = [
  { key: "all", label: "智能收件箱", icon: "收" },
  { key: "important", label: "重要消息", icon: "重" },
  { key: "todo", label: "待办事项", icon: "待" },
  { key: "unread", label: "未读消息", icon: "未" },
  { key: "official", label: "学校与学院", icon: "校" },
  { key: "course", label: "课程与班级", icon: "课" },
  { key: "service", label: "校园事务", icon: "办" },
  { key: "collaboration", label: "协作与群聊", icon: "协" },
];

function conversationToNotice(conversation: ConversationListItem): NoticeItem {
  const title = conversation.title || (conversation.type === "PRIVATE" ? "个人沟通" : "校园协作群聊");
  return {
    id: `conversation-${conversation.id}`,
    category: "collaboration",
    source: conversation.type === "SCENE" ? "协作空间" : "校园沟通",
    title,
    summary: `这是一个包含 ${conversation.participant_count} 位参与者的校园沟通空间，可查看最新消息与公开协作进展。`,
    original: "该项目来自你的校园会话列表。打开会话后，可以查看完整消息记录、参与者以及公开的协作内容。",
    time: conversation.last_message_at ? formatDate(conversation.last_message_at) : "暂无新消息",
    priority: "normal",
    unread: false,
    actionable: false,
    status: conversation.type === "PRIVATE" ? "个人沟通" : "群体协作",
    audience: `${conversation.participant_count} 位参与者`,
    href: `/conversations/${conversation.id}`,
    actionLabel: "打开会话",
    icon: conversation.type === "PRIVATE" ? "私" : "群",
  };
}

function ConversationsContent() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<NoticeCategory>("all");
  const [selectedId, setSelectedId] = useState(DEMO_NOTICES[0].id);
  const [showDetail, setShowDetail] = useState(false);
  const [addedToTasks, setAddedToTasks] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createType, setCreateType] = useState<"private" | "group">("private");
  const [targetUserId, setTargetUserId] = useState("");
  const [groupTitle, setGroupTitle] = useState("");
  const [memberSearchQuery, setMemberSearchQuery] = useState("");
  const [memberSearchResults, setMemberSearchResults] = useState<DirectoryUserResult[]>([]);
  const [memberSearchLoading, setMemberSearchLoading] = useState(false);
  const [selectedMembers, setSelectedMembers] = useState<DirectoryUserResult[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [organizationContext, setOrganizationContext] = useState<{ id: string; name: string } | null>(null);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listConversations();
      if (result.success && result.data) setConversations(result.data.conversations);
      else setError(result.error?.message ?? "加载消息失败");
    } catch {
      setError("网络错误，请稍后重试");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchContacts = useCallback(async () => {
    const result = await listContacts();
    if (result.success && result.data) {
      setContacts(result.data.contacts);
      setTargetUserId((current) => current || result.data?.contacts[0]?.user.id || "");
    }
  }, []);

  useEffect(() => {
    void fetchConversations();
    void fetchContacts();
  }, [fetchConversations, fetchContacts]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const organizationId = params.get("organization");
    const organizationName = params.get("name");
    if (!organizationId || !organizationName) return;
    setOrganizationContext({ id: organizationId, name: organizationName });
    setCreateType("private");
    setShowCreate(true);
  }, []);

  const notices = useMemo(
    () => [...DEMO_NOTICES, ...conversations.map(conversationToNotice)],
    [conversations],
  );

  const filteredNotices = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return notices.filter((notice) => {
      const matchesCategory = activeCategory === "all"
        || (activeCategory === "important" && notice.priority !== "normal")
        || (activeCategory === "todo" && notice.actionable)
        || (activeCategory === "unread" && notice.unread)
        || notice.category === activeCategory;
      const matchesQuery = !normalizedQuery
        || `${notice.title} ${notice.source} ${notice.summary} ${notice.status ?? ""}`.toLowerCase().includes(normalizedQuery);
      return matchesCategory && matchesQuery;
    });
  }, [activeCategory, notices, query]);

  const selectedNotice = filteredNotices.find((notice) => notice.id === selectedId) ?? filteredNotices[0] ?? null;
  const unreadCount = notices.filter((notice) => notice.unread).length;
  const todoCount = notices.filter((notice) => notice.actionable).length;
  const importantCount = notices.filter((notice) => notice.priority !== "normal").length;

  const selectNotice = (notice: NoticeItem) => {
    setSelectedId(notice.id);
    setAddedToTasks(false);
    setShowDetail(true);
  };

  const handleMemberSearch = async () => {
    const query = memberSearchQuery.trim();
    setActionError(null);

    if (query.length < 2) {
      setMemberSearchResults([]);
      setActionError("请输入至少 2 个字再搜索成员");
      return;
    }

    setMemberSearchLoading(true);
    try {
      const result = await searchDirectory(query, "users", 8);
      if (result.success && result.data) {
        const selectedIds = new Set(selectedMembers.map((member) => member.id));
        setMemberSearchResults(
          result.data.users.filter((user) => !selectedIds.has(user.id))
        );
      } else {
        setActionError(result.error?.message ?? "搜索成员失败");
      }
    } catch {
      setActionError("网络错误");
    } finally {
      setMemberSearchLoading(false);
    }
  };

  const addSelectedMember = (member: DirectoryUserResult) => {
    setSelectedMembers((current) => (
      current.some((item) => item.id === member.id) ? current : [...current, member]
    ));
    setMemberSearchResults((current) => current.filter((item) => item.id !== member.id));
  };

  const removeSelectedMember = (memberId: string) => {
    setSelectedMembers((current) => current.filter((member) => member.id !== memberId));
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setActionError(null);
    setActionLoading(true);
    try {
      if (createType === "private") {
        if (!targetUserId.trim()) {
          setActionError("请选择联系人或输入用户 ID");
          return;
        }
        const result = await createPrivateConversation(targetUserId.trim());
        if (!result.success) setActionError(result.error?.message ?? "创建私聊失败");
        else {
          setShowCreate(false);
          void fetchConversations();
        }
      } else {
        if (selectedMembers.length === 0) {
          setActionError("请至少选择一位成员");
          return;
        }
        const result = await createGroupConversation({
          title: groupTitle.trim() || undefined,
          participant_user_ids: selectedMembers.map((member) => member.id),
        });
        if (!result.success) {
          setActionError(result.error?.message ?? "创建群聊失败");
        } else {
          setShowCreate(false);
          setGroupTitle("");
          setMemberSearchQuery("");
          setMemberSearchResults([]);
          setSelectedMembers([]);
          void fetchConversations();
        }
      }
    } catch {
      setActionError("网络错误，请稍后重试");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className={`notification-center${showDetail ? " is-detail-open" : ""}`}>
      <header className="notification-center-header">
        <div className="notification-title">
          <span>智能校园信息中心</span>
          <h1>消息与通知</h1>
          <p>重要信息、个人待办与校园沟通，都在这里清楚呈现。</p>
        </div>
        <label className="notification-search">
          <span aria-hidden="true">⌕</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索标题、发布部门、课程，或输入“本周需要提交的材料”"
          />
          {query && <button type="button" onClick={() => setQuery("")} aria-label="清空查询">×</button>}
        </label>
        <button className="notification-create-button" onClick={() => setShowCreate(true)}><span aria-hidden="true">＋</span>发起沟通</button>
      </header>

      <div className="notification-summary-strip" aria-label="消息概览">
        <button onClick={() => setActiveCategory("important")}><span className="is-red" /> <strong>{importantCount}</strong><small>重要消息</small></button>
        <button onClick={() => setActiveCategory("todo")}><span className="is-amber" /> <strong>{todoCount}</strong><small>需要处理</small></button>
        <button onClick={() => setActiveCategory("unread")}><span className="is-blue" /> <strong>{unreadCount}</strong><small>未读消息</small></button>
        <button onClick={() => { setQuery("截止"); setActiveCategory("all"); }}><span className="is-green" /> <strong>1</strong><small>即将截止</small></button>
        <div className="notification-quick-query"><span>快捷查询</span><button onClick={() => setQuery("课程")}>课程调整</button><button onClick={() => setQuery("申请")}>申请通知</button><button onClick={() => setQuery("办理")}>办理进度</button></div>
      </div>

      {error && <div className="notification-error" role="alert">{error}</div>}

      <div className="notification-body">
        <aside className="notification-categories" aria-label="消息分类">
          <div className="notification-category-list">
            {CATEGORY_ITEMS.map((item, index) => {
              const count = item.key === "all" ? notices.length
                : item.key === "important" ? importantCount
                  : item.key === "todo" ? todoCount
                    : item.key === "unread" ? unreadCount
                      : notices.filter((notice) => notice.category === item.key).length;
              return (
                <button
                  key={item.key}
                  className={activeCategory === item.key ? "is-active" : ""}
                  onClick={() => { setActiveCategory(item.key); setShowDetail(false); }}
                >
                  <span aria-hidden="true">{item.icon}</span><strong>{item.label}</strong><small>{count}</small>
                  {index === 3 && <i aria-hidden="true" />}
                </button>
              );
            })}
          </div>
          <div className="notification-category-foot"><span aria-hidden="true">✓</span><p><strong>信息来源可追溯</strong><small>摘要不会替代学校原始通知</small></p></div>
        </aside>

        <section className="notification-list-panel" aria-labelledby="notification-list-title">
          <header>
            <div><span>{activeCategory === "all" ? "智能收件箱" : CATEGORY_ITEMS.find((item) => item.key === activeCategory)?.label}</span><h2 id="notification-list-title">{query ? `“${query}”的查询结果` : "按重要程度排列"}</h2></div>
            <small>{filteredNotices.length} 条</small>
          </header>
          <div className="notification-list-tabs" aria-label="消息类型">
            <button className="is-active">全部</button><button onClick={() => setActiveCategory("official")}>通知</button><button onClick={() => setActiveCategory("collaboration")}>沟通</button>
          </div>
          {loading && <div className="notification-list-state">正在同步校园消息…</div>}
          {!loading && filteredNotices.length === 0 && <div className="notification-list-state"><strong>没有找到相关消息</strong><span>尝试清除查询或选择其他分类。</span></div>}
          <div className="notification-list">
            {filteredNotices.map((notice) => (
              <button key={notice.id} className={`${selectedNotice?.id === notice.id ? "is-selected" : ""}${notice.unread ? " is-unread" : ""}`} onClick={() => selectNotice(notice)}>
                <span className={`notification-source-icon is-${notice.category}`} aria-hidden="true">{notice.icon}</span>
                <span className="notification-list-copy">
                  <span><strong>{notice.source}</strong><time>{notice.time}</time></span>
                  <b>{notice.title}</b>
                  <p>{notice.summary}</p>
                  <span className="notification-tags">
                    {notice.priority !== "normal" && <em className={`is-${notice.priority}`}>{notice.priority === "urgent" ? "重要" : "关注"}</em>}
                    {notice.status && <em>{notice.status}</em>}
                    {notice.deadline && <em className="is-deadline">{notice.deadline} 截止</em>}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="notification-detail" aria-label="消息详情">
          {selectedNotice ? (
            <>
              <header className="notification-detail-header">
                <button className="notification-mobile-back" onClick={() => setShowDetail(false)} aria-label="返回消息列表">←</button>
                <span className={`notification-detail-icon is-${selectedNotice.category}`}>{selectedNotice.icon}</span>
                <div><span>{selectedNotice.source}</span><h2>{selectedNotice.title}</h2><small>{selectedNotice.time} · {selectedNotice.audience}</small></div>
                <button aria-label="收藏消息">☆</button>
              </header>

              <div className="notification-detail-scroll">
                <section className="notification-agent-summary">
                  <header><span aria-hidden="true">CA</span><div><strong>Agent 整理</strong><small>基于原始通知生成</small></div><em>摘要</em></header>
                  <p>{selectedNotice.summary}</p>
                  <div>
                    {selectedNotice.deadline && <span><small>截止时间</small><strong>{selectedNotice.deadline}</strong></span>}
                    <span><small>与你相关</small><strong>{selectedNotice.audience}</strong></span>
                    <span><small>建议操作</small><strong>{selectedNotice.actionable ? selectedNotice.actionLabel : "阅读确认"}</strong></span>
                  </div>
                </section>

                <section className="notification-original">
                  <header><div><span>原始内容</span><h3>通知正文</h3></div><button>查看来源</button></header>
                  <p>{selectedNotice.original}</p>
                  <dl>
                    <div><dt>发布单位</dt><dd>{selectedNotice.source}</dd></div>
                    <div><dt>接收范围</dt><dd>{selectedNotice.audience}</dd></div>
                    <div><dt>发布时间</dt><dd>{selectedNotice.time}</dd></div>
                    <div><dt>当前状态</dt><dd>{selectedNotice.status ?? "已发布"}</dd></div>
                  </dl>
                </section>

                {selectedNotice.actionable && (
                  <section className="notification-action-extract">
                    <span>需要行动</span><h3>{selectedNotice.actionLabel}</h3>
                    <p>Agent 已提取相关入口和必要信息，任何提交操作仍需要你最终确认。</p>
                  </section>
                )}
              </div>

              <footer className="notification-detail-actions">
                <button onClick={() => setAddedToTasks(true)} className={addedToTasks ? "is-done" : ""}>{addedToTasks ? "✓ 已加入待办" : "＋ 加入待办"}</button>
                <Link href={`/workspace?context=${encodeURIComponent(selectedNotice.title)}`}>在个人工作台处理</Link>
                <Link href={selectedNotice.href} className="is-primary">{selectedNotice.actionLabel} <span aria-hidden="true">→</span></Link>
              </footer>
            </>
          ) : <div className="notification-empty-detail"><span>⌕</span><strong>选择一条消息查看详情</strong><p>这里会显示 Agent 摘要、原始内容和可执行操作。</p></div>}
        </section>
      </div>

      {showCreate && (
        <div className="notification-dialog-backdrop" role="presentation" onMouseDown={() => setShowCreate(false)}>
          <section className="notification-create-dialog" role="dialog" aria-modal="true" aria-labelledby="create-conversation-title" onMouseDown={(event) => event.stopPropagation()}>
            <header><div><span>校园沟通</span><h2 id="create-conversation-title">{organizationContext ? `联系 ${organizationContext.name} 负责人` : "发起新的沟通"}</h2></div><button onClick={() => setShowCreate(false)} aria-label="关闭">×</button></header>
            <div className="notification-create-tabs"><button className={createType === "private" ? "is-active" : ""} onClick={() => setCreateType("private")}>个人沟通</button><button className={createType === "group" ? "is-active" : ""} onClick={() => setCreateType("group")}>创建群聊</button></div>
            <form onSubmit={handleCreate}>
              {organizationContext && <aside className="notification-organization-context"><span>组</span><p><strong>{organizationContext.name}</strong><small>本次沟通会保留组织来源，便于负责人理解上下文。</small></p></aside>}
              {createType === "private" ? (
                <label><span>选择联系人</span>{contacts.length > 0 ? <select value={targetUserId} onChange={(event) => setTargetUserId(event.target.value)}>{contacts.map((contact) => <option key={contact.user.id} value={contact.user.id}>{contact.user.display_name}</option>)}</select> : <input value={targetUserId} onChange={(event) => setTargetUserId(event.target.value)} placeholder="输入用户 ID" />}</label>
              ) : (
                <>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>群聊标题（可选）</label>
                <input
                  aria-label="群聊标题（可选）"
                  type="text"
                  value={groupTitle}
                  onChange={(e) => setGroupTitle(e.target.value)}
                  placeholder="群聊名称"
                  style={{ width: "100%", padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", marginBottom: 4, fontSize: 14, color: "#374151" }}>搜索成员</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    aria-label="搜索成员"
                    type="search"
                    value={memberSearchQuery}
                    onChange={(e) => setMemberSearchQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        void handleMemberSearch();
                      }
                    }}
                    placeholder="输入同学姓名或关键词"
                    style={{ flex: 1, padding: 8, boxSizing: "border-box", borderRadius: 4, border: "1px solid #d1d5db" }}
                  />
                  <button
                    type="button"
                    onClick={() => void handleMemberSearch()}
                    disabled={memberSearchLoading || memberSearchQuery.trim().length < 2}
                    style={{
                      padding: "8px 16px",
                      borderRadius: 6,
                      border: "1px solid #d1d5db",
                      background: memberSearchLoading || memberSearchQuery.trim().length < 2 ? "#e5e7eb" : "#fff",
                      cursor: memberSearchLoading || memberSearchQuery.trim().length < 2 ? "not-allowed" : "pointer",
                    }}
                  >
                    {memberSearchLoading ? "搜索中..." : "搜索"}
                  </button>
                </div>

                {memberSearchResults.length > 0 && (
                  <div style={{ marginTop: 8, display: "grid", gap: 6 }}>
                    {memberSearchResults.map((member) => (
                      <div
                        key={member.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 8,
                          padding: 8,
                          border: "1px solid #e5e7eb",
                          borderRadius: 6,
                          background: "#fff",
                        }}
                      >
                        <span style={{ fontSize: 14 }}>{member.display_name}</span>
                        <button
                          type="button"
                          aria-label={`添加 ${member.display_name}`}
                          onClick={() => addSelectedMember(member)}
                          style={{ padding: "4px 10px", borderRadius: 4, border: "1px solid #3b82f6", background: "#eff6ff", color: "#1d4ed8", cursor: "pointer" }}
                        >
                          添加
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <label style={{ fontSize: 14, color: "#374151" }}>已选成员</label>
                  <span style={{ fontSize: 12, color: "#6b7280" }}>{selectedMembers.length} 人</span>
                </div>
                {selectedMembers.length > 0 ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {selectedMembers.map((member) => (
                      <span
                        key={member.id}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "4px 8px",
                          border: "1px solid #bfdbfe",
                          borderRadius: 999,
                          background: "#eff6ff",
                          color: "#1e40af",
                          fontSize: 14,
                        }}
                      >
                        {member.display_name}
                        <button
                          type="button"
                          aria-label={`移除 ${member.display_name}`}
                          onClick={() => removeSelectedMember(member.id)}
                          style={{ border: "none", background: "transparent", color: "#1d4ed8", cursor: "pointer", padding: 0 }}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                ) : (
                  <p style={{ margin: 0, color: "#6b7280", fontSize: 14 }}>还没有选择成员，先搜索同学再添加。</p>
                )}
              </div>
            </>
          )}

              {actionError && <p role="alert">{actionError}</p>}
              <footer>
                <button type="button" onClick={() => setShowCreate(false)}>取消</button>
                <button type="submit" disabled={actionLoading}>{actionLoading ? "正在创建…" : "确认创建"}</button>
              </footer>
            </form>
          </section>
        </div>
      )}

    </div>
  );
}

export default function ConversationsPage() {
  return <AppShell requireAuth><ConversationsContent /></AppShell>;
}
