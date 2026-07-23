"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/app/AppShell";
import { apiDelete, apiGet, apiPatch, apiPost, isForbiddenError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth";
import { useAsync } from "@/lib/useAsync";

interface OrganizationListItem {
  id: string;
  name: string;
  type: string;
  visibility: string;
  status: string;
  member_count: number;
  description?: string | null;
  parent_id?: string | null;
  join_policy?: string | null;
  capacity?: number | null;
  created_by?: string | null;
  current_role?: string | null;
  current_membership_status?: string | null;
  role?: string | null;
}

interface OrganizationListResponse {
  organizations: OrganizationListItem[];
  total: number;
  page: number;
  page_size: number;
}

interface UserOrganizationResponse {
  organizations: OrganizationListItem[];
}

interface OrganizationMember {
  user_id: string;
  display_name: string;
  role: string;
  status: string;
}

interface MemberListResponse {
  members: OrganizationMember[];
  total: number;
}

interface DirectoryUser {
  id: string;
  display_name: string;
  avatar_url?: string | null;
}

interface DirectorySearchResponse {
  users: DirectoryUser[];
  total: number;
}

type PrimaryView = "mine" | "discover" | "managed" | "requests";
type TypeFilter = "all" | "official" | "class" | "student" | "dorm" | "project";
type DetailTab = "overview" | "members" | "requests" | "settings";

const DISCOVERABLE_MEMBERSHIP_STATUSES = new Set(["LEFT", "REMOVED"]);

function isDiscoverableOrganization(org: DirectoryOrganization) {
  return org.visibility === "PUBLIC" && (
    !org.current_membership_status ||
    DISCOVERABLE_MEMBERSHIP_STATUSES.has(org.current_membership_status)
  );
}

interface DirectoryOrganization extends OrganizationListItem {
  category: Exclude<TypeFilter, "all">;
  parent: string;
  myRole: string;
  verified: boolean;
  recent: string;
  initials: string;
  tone: "green" | "blue" | "amber" | "purple";
  people: string[];
  apiBacked?: boolean;
}

const PRIMARY_VIEWS: { id: PrimaryView; icon: string; label: string; note: string }[] = [
  { id: "mine", icon: "我", label: "我的群体", note: "已经加入的校园关系" },
  { id: "discover", icon: "寻", label: "发现组织", note: "可了解和申请加入" },
  { id: "managed", icon: "管", label: "我管理的", note: "成员、规则与申请" },
  { id: "requests", icon: "审", label: "申请与邀请", note: "查看当前处理进度" },
];

const TYPE_FILTERS: { id: TypeFilter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "official", label: "学校组织" },
  { id: "class", label: "班级课程" },
  { id: "student", label: "社团" },
  { id: "dorm", label: "宿舍" },
  { id: "project", label: "项目小组" },
];

const FALLBACK_ORGANIZATIONS: DirectoryOrganization[] = [
  {
    id: "sample-college", name: "信息科学技术学院", type: "COLLEGE", visibility: "PUBLIC", status: "ACTIVE", member_count: 3286,
    description: "连接学院教学、科研与学生服务的官方组织空间。", join_policy: "CLOSED", current_role: "MEMBER", current_membership_status: "ACTIVE",
    category: "official", parent: "暨南大学", myRole: "本科生", verified: true, recent: "奖学金申请通知 · 今天 09:30", initials: "院", tone: "green", people: ["陈老师", "李同学", "王同学", "周老师"],
  },
  {
    id: "sample-course", name: "人工智能", type: "COURSE", visibility: "MEMBERS_ONLY", status: "ACTIVE", member_count: 46,
    description: "人工智能课程通知、学习资料和课程协作空间。", join_policy: "CLOSED", current_role: "MEMBER", current_membership_status: "ACTIVE",
    category: "class", parent: "信息科学技术学院", myRole: "课程成员", verified: true, recent: "课程资料已更新 · 昨天", initials: "课", tone: "blue", people: ["张老师", "陈同学", "黄同学", "Alice"],
  },
  {
    id: "sample-club", name: "模型互联网", type: "CLUB", visibility: "PUBLIC", status: "ACTIVE", member_count: 86,
    description: "面向暨南大学学生的模型互联网兴趣交流与实践社团。", join_policy: "APPROVAL", current_role: "MEMBER", current_membership_status: "ACTIVE",
    category: "student", parent: "学生社团管理中心", myRole: "社团成员", verified: false, recent: "本周技术分享 · 2天前", initials: "模", tone: "purple", people: ["许会长", "罗同学", "梁同学", "Alice"],
  },
  {
    id: "sample-project", name: "Campus Agent", type: "TEAM", visibility: "MEMBERS_ONLY", status: "ACTIVE", member_count: 12,
    description: "Campus Agent 项目交流、任务协作与共同建设空间。", join_policy: "APPROVAL", current_role: "OWNER", current_membership_status: "ACTIVE",
    category: "project", parent: "信息科学技术学院", myRole: "负责人", verified: false, recent: "共识文档有 3 项更新 · 今天", initials: "CA", tone: "amber", people: ["Alice", "陈老师", "林同学", "共识 Agent"],
  },
  {
    id: "sample-lab", name: "WNDS实验室", type: "LAB", visibility: "MEMBERS_ONLY", status: "ACTIVE", member_count: 18,
    description: "模型互联网与智能系统研究、讨论和项目协作空间。", join_policy: "INVITE_ONLY", current_role: "OWNER", current_membership_status: "ACTIVE",
    category: "project", parent: "信息科学技术学院", myRole: "负责人", verified: false, recent: "实验室周会安排 · 今天", initials: "WN", tone: "blue", people: ["Alice", "陈老师", "研究生甲", "研究生乙"],
  },
  {
    id: "sample-dorm", name: "东9 T207", type: "DORM", visibility: "PRIVATE", status: "ACTIVE", member_count: 4,
    description: "由学校住宿关系同步，用于寝室公共事项与日常协商。", join_policy: "CLOSED", current_role: "MEMBER", current_membership_status: "ACTIVE",
    category: "dorm", parent: "石牌校区 · 东9栋", myRole: "寝室成员", verified: true, recent: "本周寝室卫生安排 · 今天", initials: "207", tone: "green", people: ["Alice", "陈同学", "林同学", "王同学"],
  },
];

const CREATE_TYPES = [
  { id: "STUDY", apiType: "TEAM", icon: "学", title: "学习小组", note: "课程互助、考试复习与资料共建" },
  { id: "PROJECT", apiType: "TEAM", icon: "项", title: "项目团队", note: "比赛、科研与跨专业项目协作" },
  { id: "ACTIVITY", apiType: "OTHER", icon: "活", title: "校园活动", note: "活动组织、志愿服务与临时筹备" },
  { id: "CLUB", apiType: "CLUB", icon: "社", title: "学生社团申请", note: "提交后进入学校认证审核流程" },
  { id: "INTEREST", apiType: "OTHER", icon: "趣", title: "兴趣群体", note: "兴趣交流、运动约伴与校园生活" },
  { id: "DISCUSSION", apiType: "OTHER", icon: "议", title: "临时协商群体", note: "围绕具体议题进行限时沟通" },
];

function typeLabel(type: string) {
  const labels: Record<string, string> = { SCHOOL: "学校", COLLEGE: "学院", DEPARTMENT: "院系", CLASS: "班级", DORM: "宿舍", CLUB: "社团", COURSE: "课程", LAB: "实验室", TEAM: "项目组", OTHER: "群体" };
  return labels[type] ?? "群体";
}

function categoryForType(type: string): DirectoryOrganization["category"] {
  if (["SCHOOL", "COLLEGE", "DEPARTMENT"].includes(type)) return "official";
  if (["CLASS", "COURSE"].includes(type)) return "class";
  if (type === "CLUB") return "student";
  if (type === "DORM") return "dorm";
  return "project";
}

function roleLabel(role?: string | null) {
  return ({ OWNER: "负责人", ADMIN: "管理员", MEMBER: "成员", GUEST: "观察成员" } as Record<string, string>)[role ?? ""] ?? "尚未加入";
}

function joinPolicyLabel(policy?: string | null) {
  return ({ OPEN: "校内成员可直接加入", APPROVAL: "申请后由负责人审核", INVITE_ONLY: "仅邀请加入", CLOSED: "由学校身份关系同步" } as Record<string, string>)[policy ?? ""] ?? "查看组织规则";
}

function visibilityLabel(visibility: string) {
  return ({ PUBLIC: "校内公开", MEMBERS_ONLY: "仅成员可查看", PRIVATE: "仅受邀成员可见" } as Record<string, string>)[visibility] ?? visibility;
}

function OrganizationsContent() {
  const { user } = useAuth();
  const [view, setView] = useState<PrimaryView>("mine");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [detailTab, setDetailTab] = useState<DetailTab>("overview");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [showDetail, setShowDetail] = useState(false);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [leaveConfirmId, setLeaveConfirmId] = useState<string | null>(null);
  const [memberSearch, setMemberSearch] = useState("");
  const [memberRoleFilter, setMemberRoleFilter] = useState("ALL");
  const [showInvite, setShowInvite] = useState(false);
  const [inviteQuery, setInviteQuery] = useState("");
  const [inviteSearchTerm, setInviteSearchTerm] = useState("");
  const [inviteRole, setInviteRole] = useState("MEMBER");
  const [memberActionId, setMemberActionId] = useState<string | null>(null);
  const [settingsName, setSettingsName] = useState("");
  const [settingsDescription, setSettingsDescription] = useState("");
  const [settingsJoinPolicy, setSettingsJoinPolicy] = useState("APPROVAL");
  const [settingsVisibility, setSettingsVisibility] = useState("MEMBERS_ONLY");
  const [settingsCapacity, setSettingsCapacity] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createStep, setCreateStep] = useState(1);
  const [createType, setCreateType] = useState("STUDY");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [parentId, setParentId] = useState("");
  const [joinPolicy, setJoinPolicy] = useState("APPROVAL");
  const [visibility, setVisibility] = useState("MEMBERS_ONLY");
  const [capacity, setCapacity] = useState("50");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const { data, loading, error, reload } = useAsync<OrganizationListResponse>(() => apiGet("/organizations", { page_size: "100" }), []);
  const { data: mineData, reload: reloadMine } = useAsync<UserOrganizationResponse>(
    async () => user ? apiGet(`/users/${user.id}/organizations`) : { organizations: [] },
    [user?.id],
  );

  const apiOrganizations = useMemo<DirectoryOrganization[]>(() => {
    const myRoles = new Map((mineData?.organizations ?? []).map((org) => [org.id, org.role ?? org.current_role]));
    return (data?.organizations ?? []).map((org, index) => {
      const currentRole = org.current_role ?? myRoles.get(org.id) ?? null;
      const membershipStatus = org.current_membership_status ?? (currentRole ? "ACTIVE" : null);
      return {
        ...org,
        current_role: currentRole,
        current_membership_status: membershipStatus,
        category: categoryForType(org.type),
        description: org.description || "由校园成员通过统一身份参与的组织空间。",
        parent: "暨南大学",
        myRole: membershipStatus === "PENDING" ? "申请审核中" : membershipStatus === "INVITED" ? "等待你确认" : DISCOVERABLE_MEMBERSHIP_STATUSES.has(membershipStatus ?? "") ? "可重新加入" : roleLabel(currentRole),
        verified: ["SCHOOL", "COLLEGE", "DEPARTMENT", "CLASS", "COURSE", "DORM"].includes(org.type),
        recent: membershipStatus === "ACTIVE" ? "查看最新动态与协作" : "查看组织详情与加入规则",
        initials: typeLabel(org.type).slice(0, 2),
        tone: (["green", "blue", "amber", "purple"] as const)[index % 4],
        people: [],
        apiBacked: true,
      };
    });
  }, [data, mineData]);

  const organizations = apiOrganizations.length ? apiOrganizations : FALLBACK_ORGANIZATIONS;

  const counts = useMemo(() => ({
    mine: organizations.filter((org) => org.current_membership_status === "ACTIVE").length,
    discover: organizations.filter(isDiscoverableOrganization).length,
    managed: organizations.filter((org) => org.current_membership_status === "ACTIVE" && ["OWNER", "ADMIN"].includes(org.current_role ?? "")).length,
    requests: organizations.filter((org) => ["PENDING", "INVITED"].includes(org.current_membership_status ?? "")).length,
  }), [organizations]);

  const filteredOrganizations = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return organizations.filter((org) => {
      const matchesView = view === "mine" ? org.current_membership_status === "ACTIVE" :
        view === "discover" ? isDiscoverableOrganization(org) :
        view === "managed" ? org.current_membership_status === "ACTIVE" && ["OWNER", "ADMIN"].includes(org.current_role ?? "") :
        ["PENDING", "INVITED"].includes(org.current_membership_status ?? "");
      const matchesType = typeFilter === "all" || org.category === typeFilter;
      const matchesSearch = !keyword || `${org.name} ${org.parent} ${org.description} ${typeLabel(org.type)}`.toLowerCase().includes(keyword);
      return matchesView && matchesType && matchesSearch;
    });
  }, [organizations, search, typeFilter, view]);

  const selected = filteredOrganizations.find((org) => org.id === selectedId) ?? filteredOrganizations[0] ?? null;
  const isManager = selected?.current_membership_status === "ACTIVE" && ["OWNER", "ADMIN"].includes(selected.current_role ?? "");
  const isActiveMember = selected?.current_membership_status === "ACTIVE";

  const { data: memberData, loading: memberLoading, reload: reloadMembers } = useAsync<MemberListResponse>(
    async () => selected?.apiBacked && isActiveMember ? apiGet(`/organizations/${selected.id}/members`) : { members: [], total: 0 },
    [selected?.id, selected?.apiBacked, isActiveMember],
  );
  const { data: requestData, loading: requestLoading, reload: reloadRequests } = useAsync<MemberListResponse>(
    async () => selected?.apiBacked && isManager ? apiGet(`/organizations/${selected.id}/members`, { status_filter: "PENDING" }) : { members: [], total: 0 },
    [selected?.id, selected?.apiBacked, isManager],
  );
  const { data: invitedData, reload: reloadInvited } = useAsync<MemberListResponse>(
    async () => selected?.apiBacked && isManager ? apiGet(`/organizations/${selected.id}/members`, { status_filter: "INVITED" }) : { members: [], total: 0 },
    [selected?.id, selected?.apiBacked, isManager],
  );
  const { data: directoryResults, loading: directoryLoading } = useAsync<DirectorySearchResponse>(
    async () => inviteSearchTerm.length >= 2 ? apiGet("/directory/search", { q: inviteSearchTerm, type: "users", limit: "8" }) : { users: [], total: 0 },
    [inviteSearchTerm],
  );

  const filteredMembers = useMemo(() => (memberData?.members ?? []).filter((member) => {
    const matchesName = !memberSearch.trim() || member.display_name.toLowerCase().includes(memberSearch.trim().toLowerCase());
    const matchesRole = memberRoleFilter === "ALL" || member.role === memberRoleFilter;
    return matchesName && matchesRole;
  }), [memberData, memberRoleFilter, memberSearch]);

  useEffect(() => {
    if (!selected) return;
    setSettingsName(selected.name);
    setSettingsDescription(selected.description ?? "");
    setSettingsJoinPolicy(selected.join_policy ?? "APPROVAL");
    setSettingsVisibility(selected.visibility);
    setSettingsCapacity(selected.capacity ? String(selected.capacity) : "");
  }, [selected]);

  const selectedCreateType = CREATE_TYPES.find((item) => item.id === createType) ?? CREATE_TYPES[0];
  const possibleParents = organizations.filter((org) => org.verified && org.current_membership_status === "ACTIVE" && org.apiBacked);
  const activeView = PRIMARY_VIEWS.find((item) => item.id === view) ?? PRIMARY_VIEWS[0];
  const isForbidden = error && isForbiddenError(error);

  const changeView = (nextView: PrimaryView) => {
    setView(nextView);
    setTypeFilter("all");
    setSelectedId("");
    setShowDetail(false);
    setDetailTab(nextView === "managed" ? "members" : "overview");
    setActionMessage(null);
  };

  const refreshOrganizations = async () => {
    await Promise.all([reload(), reloadMine(), reloadMembers(), reloadRequests(), reloadInvited()]);
  };

  const handleMembershipAction = async (action: "join" | "leave") => {
    if (action === "leave" && selected?.current_role === "OWNER") {
      setLeaveConfirmId(null);
      setActionMessage("请先转让负责人身份，再退出群体。");
      return;
    }
    if (!selected?.apiBacked) {
      setActionMessage(action === "join" ? "演示组织已收到你的加入申请。" : "演示组织已退出。");
      setLeaveConfirmId(null);
      return;
    }
    setActing(true);
    setActionMessage(null);
    try {
      const result = await apiPost<{ status?: string }>(`/organizations/${selected.id}/${action}`);
      const organizationId = selected.id;
      const shouldReturnToDiscover = action === "leave" && selected.visibility === "PUBLIC";
      setLeaveConfirmId(null);
      await refreshOrganizations();
      if (shouldReturnToDiscover) {
        setView("discover");
        setTypeFilter("all");
        setSelectedId(organizationId);
        setShowDetail(true);
        setDetailTab("overview");
      }
      setActionMessage(action === "leave" ? shouldReturnToDiscover ? "已退出该群体，你仍可在发现组织中重新加入。" : "已退出该群体。" : result?.status === "PENDING" ? "申请已提交，等待负责人审核。" : "已加入该群体。");
    } catch (actionError) {
      setActionMessage(actionError instanceof Error ? actionError.message : "操作失败，请稍后重试。");
    } finally {
      setActing(false);
    }
  };

  const reviewRequest = async (member: OrganizationMember, decision: "APPROVE" | "REJECT") => {
    if (!selected?.apiBacked) return;
    setActing(true);
    setActionMessage(null);
    try {
      await apiPost(`/organizations/${selected.id}/members/${member.user_id}/review`, { decision, role: "MEMBER" });
      setActionMessage(decision === "APPROVE" ? `已同意 ${member.display_name} 加入。` : `已拒绝 ${member.display_name} 的申请。`);
      reloadRequests();
      reloadMembers();
    } catch (reviewError) {
      setActionMessage(reviewError instanceof Error ? reviewError.message : "审核失败，请稍后重试。");
    } finally {
      setActing(false);
    }
  };

  const decideInvitation = async (decision: "ACCEPT" | "DECLINE") => {
    if (!selected?.apiBacked) return;
    setActing(true);
    setActionMessage(null);
    try {
      await apiPost(`/organizations/${selected.id}/invitation`, { decision });
      setActionMessage(decision === "ACCEPT" ? "已接受邀请并加入群体。" : "已谢绝本次邀请。");
      refreshOrganizations();
    } catch (invitationError) {
      setActionMessage(invitationError instanceof Error ? invitationError.message : "邀请处理失败。");
    } finally {
      setActing(false);
    }
  };

  const updateMemberRole = async (member: OrganizationMember, role: string) => {
    if (!selected?.apiBacked || member.role === role) return;
    setMemberActionId(member.user_id);
    setActionMessage(null);
    try {
      await apiPatch(`/organizations/${selected.id}/members/${member.user_id}`, { role });
      setActionMessage(`已将 ${member.display_name} 设置为${roleLabel(role)}。`);
      reloadMembers();
    } catch (memberError) {
      setActionMessage(memberError instanceof Error ? memberError.message : "角色修改失败。");
    } finally {
      setMemberActionId(null);
    }
  };

  const removeMember = async (member: OrganizationMember) => {
    if (!selected?.apiBacked) return;
    setMemberActionId(member.user_id);
    setActionMessage(null);
    try {
      await apiDelete(`/organizations/${selected.id}/members/${member.user_id}`);
      setActionMessage(`已将 ${member.display_name} 移出群体。`);
      reloadMembers();
      reload();
    } catch (memberError) {
      setActionMessage(memberError instanceof Error ? memberError.message : "移除成员失败。");
    } finally {
      setMemberActionId(null);
    }
  };

  const transferOwnership = async (member: OrganizationMember) => {
    if (!selected?.apiBacked) return;
    setMemberActionId(member.user_id);
    setActionMessage(null);
    try {
      await apiPost(`/organizations/${selected.id}/ownership-transfer`, { user_id: member.user_id });
      setActionMessage(`负责人已转让给 ${member.display_name}，你现在是管理员。`);
      refreshOrganizations();
    } catch (memberError) {
      setActionMessage(memberError instanceof Error ? memberError.message : "负责人转让失败。");
    } finally {
      setMemberActionId(null);
    }
  };

  const inviteMember = async (directoryUser: DirectoryUser) => {
    if (!selected?.apiBacked) return;
    setMemberActionId(directoryUser.id);
    setActionMessage(null);
    try {
      await apiPost(`/organizations/${selected.id}/invitations`, { user_id: directoryUser.id, role: inviteRole });
      setActionMessage(`已向 ${directoryUser.display_name} 发送邀请。`);
      reloadInvited();
    } catch (inviteError) {
      setActionMessage(inviteError instanceof Error ? inviteError.message : "邀请发送失败。");
    } finally {
      setMemberActionId(null);
    }
  };

  const saveOrganizationSettings = async (event: FormEvent) => {
    event.preventDefault();
    if (!selected?.apiBacked) return;
    setActing(true);
    setActionMessage(null);
    try {
      await apiPatch(`/organizations/${selected.id}`, {
        name: settingsName.trim(),
        description: settingsDescription.trim() || null,
        join_policy: settingsJoinPolicy,
        visibility: settingsVisibility,
        capacity: settingsCapacity ? Number(settingsCapacity) : undefined,
      });
      setActionMessage("群体设置已保存。");
      reload();
    } catch (settingsError) {
      setActionMessage(settingsError instanceof Error ? settingsError.message : "设置保存失败。");
    } finally {
      setActing(false);
    }
  };

  const openCreate = () => {
    setCreateStep(1);
    setCreateError(null);
    setShowCreate(true);
  };

  const closeCreate = () => {
    if (!creating) setShowCreate(false);
  };

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (createStep < 4) {
      setCreateStep((step) => step + 1);
      return;
    }
    if (!name.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      await apiPost("/organizations", {
        name: name.trim(), type: selectedCreateType.apiType, description: description.trim() || undefined,
        visibility, join_policy: joinPolicy, parent_id: parentId || undefined,
        capacity: capacity ? Number(capacity) : undefined,
      });
      setShowCreate(false);
      setName(""); setDescription(""); setParentId(""); setCapacity("50"); setCreateStep(1);
      changeView("managed");
      refreshOrganizations();
    } catch (createFailure) {
      setCreateError(createFailure instanceof Error ? createFailure.message : "创建群体失败");
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <section className={`organization-directory organization-hub-v2${showDetail ? " is-detail-open" : ""}`} aria-label="组织与群体">
        <header className="organization-directory-header">
          <div><span>暨南大学校园关系</span><h1>组织与群体</h1><p>找到你所在的群体，也让每一次加入、管理和协作都有清晰边界。</p></div>
          <label className="organization-search"><span aria-hidden="true">⌕</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索组织名称、类型或上级组织" />{search && <button type="button" onClick={() => setSearch("")} aria-label="清空搜索">×</button>}</label>
          <button className="organization-create-button" type="button" onClick={openCreate}><span>＋</span>创建群体</button>
        </header>

        <div className="organization-directory-body">
          <aside className="organization-directory-nav organization-primary-nav" aria-label="组织功能">
            <div className="organization-directory-nav-title"><strong>组织中心</strong><small>先选择你要处理的事情</small></div>
            <div className="organization-directory-nav-list">
              {PRIMARY_VIEWS.map((item) => <button key={item.id} className={view === item.id ? "is-active" : ""} type="button" onClick={() => changeView(item.id)}><span>{item.icon}</span><strong>{item.label}</strong><small>{counts[item.id]}</small><em>{item.note}</em></button>)}
            </div>
            <div className="organization-directory-trust"><span>✓</span><p><strong>身份关系可信</strong><small>班级、课程与寝室由学校系统同步</small></p></div>
          </aside>

          <section className="organization-list-panel" aria-label="组织列表">
            <header><div><span>{activeView.label}</span><h2>{search ? `“${search}”的搜索结果` : activeView.note}</h2></div><small>{filteredOrganizations.length} 个</small></header>
            <div className="organization-list-tabs" aria-label="组织类型筛选">
              {TYPE_FILTERS.map((item) => <button key={item.id} className={typeFilter === item.id ? "is-active" : ""} type="button" onClick={() => { setTypeFilter(item.id); setSelectedId(""); }}>{item.label}</button>)}
            </div>

            {loading && <p className="organization-list-state">正在同步校园组织关系…</p>}
            {isForbidden && <p className="organization-list-state is-error">当前身份无权查看组织目录。</p>}
            {error && !isForbidden && <p className="organization-list-state is-error">组织数据暂时无法同步，已展示本地校园目录。</p>}
            <div className="organization-list">
              {filteredOrganizations.map((org) => <button key={org.id} type="button" className={selected?.id === org.id ? "is-selected" : ""} onClick={() => { setSelectedId(org.id); setShowDetail(true); setDetailTab(view === "managed" ? "members" : "overview"); setActionMessage(null); setLeaveConfirmId(null); setShowInvite(false); }}>
                <span className={`organization-avatar is-${org.tone}`}>{org.initials}</span>
                <span className="organization-list-copy"><span><strong>{org.name}</strong>{org.verified && <em>官方</em>}{org.current_membership_status === "PENDING" && <em className="is-pending">审核中</em>}{org.current_membership_status === "INVITED" && <em className="is-invited">待确认邀请</em>}</span><small>{org.parent}</small><span className="organization-list-meta"><b>{org.member_count} 人</b><i>{org.myRole}</i><time>{org.recent}</time></span></span>
              </button>)}
              {!filteredOrganizations.length && !loading && <div className="organization-empty-list"><span>{view === "requests" ? "✓" : "⌕"}</span><strong>{view === "requests" ? "暂时没有待处理事项" : "没有找到符合条件的组织"}</strong><p>{view === "discover" ? "可以换一个类型，或搜索其他校园组织。" : "切换左侧入口查看其他组织关系。"}</p></div>}
            </div>
          </section>

          {selected ? <section className="organization-detail" aria-label="组织详情">
            <header className="organization-detail-header"><button className="organization-mobile-back" type="button" onClick={() => setShowDetail(false)} aria-label="返回组织列表">←</button><span className={`organization-avatar is-${selected.tone}`}>{selected.initials}</span><div><span>{typeLabel(selected.type)} · {selected.verified ? "学校关系认证" : "成员自建"}</span><h2>{selected.name}</h2><small>{selected.parent}</small></div><button className={favorites.includes(selected.id) ? "is-favorite" : ""} type="button" onClick={() => setFavorites((items) => items.includes(selected.id) ? items.filter((id) => id !== selected.id) : [...items, selected.id])} aria-label={favorites.includes(selected.id) ? "取消收藏" : "收藏组织"}>{favorites.includes(selected.id) ? "★" : "☆"}</button></header>
            <nav className="organization-detail-tabs" aria-label="组织详情导航"><button className={detailTab === "overview" ? "is-active" : ""} type="button" onClick={() => setDetailTab("overview")}>概览</button>{isActiveMember && <button className={detailTab === "members" ? "is-active" : ""} type="button" onClick={() => setDetailTab("members")}>{isManager ? "成员管理" : "成员"} <span>{memberData?.total ?? selected.member_count}</span></button>}{isManager && <button className={detailTab === "requests" ? "is-active" : ""} type="button" onClick={() => setDetailTab("requests")}>加入申请 <span>{requestData?.total ?? 0}</span></button>}{isManager && !selected.verified && <button className={detailTab === "settings" ? "is-active" : ""} type="button" onClick={() => setDetailTab("settings")}>群体设置</button>}</nav>

            <div className="organization-detail-scroll">
              {detailTab === "overview" && <>
                <section className="organization-identity-card"><header><div><span>可信关系</span><strong>你在这个组织中的身份</strong></div><em>{selected.current_membership_status === "PENDING" ? "申请审核中" : selected.myRole}</em></header><p>{selected.description}</p><dl><div><dt>成员规模</dt><dd>{selected.member_count}{selected.capacity ? ` / ${selected.capacity}` : ""} 人</dd></div><div><dt>加入方式</dt><dd>{joinPolicyLabel(selected.join_policy)}</dd></div><div><dt>可见范围</dt><dd>{visibilityLabel(selected.visibility)}</dd></div></dl></section>
                <section className="organization-section"><header><div><span>当前入口</span><h3>{isActiveMember ? "从这里进入群体工作" : "了解清楚后再决定是否加入"}</h3></div></header><div className="organization-context-actions"><Link href={{ pathname: "/scenes", query: { organization: selected.id, name: selected.name } }}><span>协</span><div><strong>群体协作空间</strong><small>查看这个群体的投票、任务与共同结果</small></div><i>→</i></Link><Link href={{ pathname: "/conversations", query: { organization: selected.id, name: selected.name } }}><span>联</span><div><strong>联系负责人</strong><small>发起一条带有组织上下文的校园沟通</small></div><i>→</i></Link></div></section>
                <section className="organization-section"><header><div><span>最近动态</span><h3>组织正在发生什么</h3></div></header><div className="organization-recent"><span>新</span><div><strong>{selected.recent.split(" · ")[0]}</strong><small>{selected.recent.split(" · ")[1] ?? "刚刚更新"}</small></div></div></section>
                <aside className="organization-privacy-note"><span>隐私边界</span><p>组织负责人只能处理必要的校园身份、成员关系和群体公开内容，不能读取成员的私人 Agent 记忆、心理信息或个人知识库。</p></aside>
              </>}

              {detailTab === "members" && <section className={`organization-member-directory${isManager ? " is-managed" : ""}`}>
                <header><div><span>{isManager ? "负责人工作区" : "成员目录"}</span><h3>{isManager ? "成员管理" : "与你共同参与的人"}</h3></div>{isManager ? <button type="button" onClick={() => setShowInvite((value) => !value)}>＋ 邀请成员</button> : <small>只展示组织协作所需的公开身份</small>}</header>
                {actionMessage && <p className="organization-action-message">{actionMessage}</p>}
                {isManager && <div className="organization-member-toolbar"><label><span>⌕</span><input value={memberSearch} onChange={(event) => setMemberSearch(event.target.value)} placeholder="搜索成员姓名" /></label><select value={memberRoleFilter} onChange={(event) => setMemberRoleFilter(event.target.value)} aria-label="按角色筛选"><option value="ALL">全部角色</option><option value="OWNER">负责人</option><option value="ADMIN">管理员</option><option value="MEMBER">普通成员</option><option value="GUEST">观察成员</option></select></div>}
                {showInvite && isManager && <aside className="organization-invite-panel"><header><div><strong>邀请校园成员</strong><small>按姓名或暨南大学账号查找，不需要复制用户 ID</small></div><button type="button" onClick={() => setShowInvite(false)}>×</button></header><form onSubmit={(event) => { event.preventDefault(); setInviteSearchTerm(inviteQuery.trim()); }}><input value={inviteQuery} onChange={(event) => setInviteQuery(event.target.value)} placeholder="输入姓名或校园账号" /><select value={inviteRole} onChange={(event) => setInviteRole(event.target.value)}><option value="MEMBER">普通成员</option><option value="ADMIN">管理员</option><option value="GUEST">观察成员</option></select><button type="submit" disabled={inviteQuery.trim().length < 2}>搜索</button></form><div>{directoryLoading ? <p>正在搜索校园通讯录…</p> : directoryResults?.users.length ? directoryResults.users.map((directoryUser) => <article key={directoryUser.id}><span>{directoryUser.display_name.slice(0, 1)}</span><div><strong>{directoryUser.display_name}</strong><small>暨南大学统一身份</small></div><button type="button" onClick={() => inviteMember(directoryUser)} disabled={memberActionId === directoryUser.id}>{memberActionId === directoryUser.id ? "发送中…" : "发送邀请"}</button></article>) : inviteSearchTerm && <p>没有找到符合条件的校园成员。</p>}</div></aside>}
                {memberLoading ? <p className="organization-list-state">正在加载成员…</p> : <div className="organization-member-table">{filteredMembers.map((member) => <article key={member.user_id}><span>{member.display_name.slice(0, 1)}</span><div><strong>{member.display_name}{member.user_id === user?.id && <em>你</em>}</strong><small>暨南大学成员 · {member.status === "ACTIVE" ? "已加入" : member.status}</small></div>{isManager ? <select value={member.role} onChange={(event) => updateMemberRole(member, event.target.value)} disabled={memberActionId === member.user_id || (member.role === "OWNER" && member.user_id === user?.id)} aria-label={`修改${member.display_name}的角色`}><option value="OWNER">负责人</option><option value="ADMIN">管理员</option><option value="MEMBER">普通成员</option><option value="GUEST">观察成员</option></select> : <em>{roleLabel(member.role)}</em>}{isManager && <aside>{selected.current_role === "OWNER" && member.user_id !== user?.id && <button type="button" onClick={() => transferOwnership(member)} disabled={memberActionId === member.user_id}>转让负责人</button>}{member.user_id !== user?.id && member.role !== "OWNER" && <button className="is-danger" type="button" onClick={() => removeMember(member)} disabled={memberActionId === member.user_id}>移除</button>}</aside>}</article>)}</div>}
                {isManager && invitedData?.members.length ? <div className="organization-outgoing-invites"><header><strong>等待成员确认的邀请</strong><small>{invitedData.total} 人</small></header>{invitedData.members.map((member) => <article key={member.user_id}><span>{member.display_name.slice(0, 1)}</span><div><strong>{member.display_name}</strong><small>已邀请为{roleLabel(member.role)}</small></div><em>等待确认</em></article>)}</div> : null}
              </section>}

              {detailTab === "requests" && <section className="organization-request-center"><header><div><span>负责人工作区</span><h3>加入申请</h3></div><small>重要成员决定由负责人最终确认</small></header>{actionMessage && <p className="organization-action-message">{actionMessage}</p>}{requestLoading ? <p className="organization-list-state">正在加载申请…</p> : requestData?.members.length ? <div>{requestData.members.map((member) => <article key={member.user_id}><span>{member.display_name.slice(0, 1)}</span><div><strong>{member.display_name}</strong><small>申请加入 · 等待审核</small></div><aside><button type="button" onClick={() => reviewRequest(member, "REJECT")} disabled={acting}>拒绝</button><button className="is-primary" type="button" onClick={() => reviewRequest(member, "APPROVE")} disabled={acting}>同意加入</button></aside></article>)}</div> : <div className="organization-empty-list"><span>✓</span><strong>没有待审核申请</strong><p>新的加入申请会集中显示在这里。</p></div>}</section>}

              {detailTab === "settings" && isManager && <form className="organization-management-settings" onSubmit={saveOrganizationSettings}><header><div><span>群体管理</span><h3>基本设置与加入规则</h3></div><small>只有负责人和管理员可以修改</small></header>{actionMessage && <p className="organization-action-message">{actionMessage}</p>}<label><span>群体名称</span><input value={settingsName} onChange={(event) => setSettingsName(event.target.value)} required /></label><label><span>群体简介</span><textarea value={settingsDescription} onChange={(event) => setSettingsDescription(event.target.value)} rows={4} /></label><div><label><span>加入方式</span><select value={settingsJoinPolicy} onChange={(event) => setSettingsJoinPolicy(event.target.value)}><option value="APPROVAL">申请后审核</option><option value="OPEN">开放加入</option><option value="INVITE_ONLY">仅邀请</option><option value="CLOSED">关闭加入</option></select></label><label><span>可见范围</span><select value={settingsVisibility} onChange={(event) => setSettingsVisibility(event.target.value)}><option value="PUBLIC">校内公开</option><option value="MEMBERS_ONLY">仅成员可见</option><option value="PRIVATE">仅受邀成员可见</option></select></label></div><label><span>成员容量</span><input type="number" min="1" max="5000" value={settingsCapacity} onChange={(event) => setSettingsCapacity(event.target.value)} placeholder="不填写表示不限" /></label><aside><strong>隐私与责任边界</strong><p>群体设置只影响成员关系和群体公开内容，不会开放成员私人 Agent、心理信息或个人知识库。</p></aside><footer><button className="is-primary" type="submit" disabled={acting}>{acting ? "正在保存…" : "保存设置"}</button></footer></form>}
            </div>

            <footer className="organization-detail-actions">
              {actionMessage && detailTab !== "requests" && <small>{actionMessage}</small>}
              {selected.current_membership_status === "INVITED" ? <><button type="button" onClick={() => decideInvitation("DECLINE")} disabled={acting}>谢绝邀请</button><button className="is-primary" type="button" onClick={() => decideInvitation("ACCEPT")} disabled={acting}>接受并加入</button></> : selected.current_membership_status === "PENDING" ? <button type="button" disabled>申请审核中</button> : !isActiveMember && ["OPEN", "APPROVAL"].includes(selected.join_policy ?? "") ? <button className="is-primary" type="button" onClick={() => handleMembershipAction("join")} disabled={acting}>{selected.join_policy === "OPEN" ? "加入群体" : "申请加入"}</button> : !isActiveMember ? <button type="button" disabled>{selected.join_policy === "INVITE_ONLY" ? "仅限邀请" : "身份自动同步"}</button> : <>
                {leaveConfirmId === selected.id ? <span className="organization-leave-confirm"><strong>确认退出这个群体？</strong><button type="button" onClick={() => setLeaveConfirmId(null)}>取消</button><button className="is-danger" type="button" onClick={() => handleMembershipAction("leave")} disabled={acting}>{acting ? "正在退出…" : "确认退出"}</button></span> : <button className="is-danger" type="button" onClick={() => selected.current_role === "OWNER" ? handleMembershipAction("leave") : setLeaveConfirmId(selected.id)}>退出群体</button>}
                <Link href={{ pathname: "/conversations", query: { organization: selected.id, name: selected.name } }}>联系负责人</Link>
                <Link className="is-primary" href={{ pathname: "/scenes", query: { organization: selected.id, name: selected.name } }}>进入协作空间 <span>→</span></Link>
              </>}
            </footer>
          </section> : <section className="organization-detail organization-empty-detail"><span>◎</span><strong>{view === "requests" ? "申请状态清晰可见" : "选择一个组织"}</strong><p>{view === "discover" ? "查看加入规则，并决定是否申请加入。" : "查看成员关系、群体入口与管理事项。"}</p></section>}
        </div>
      </section>

      {showCreate && <div className="organization-create-backdrop" onMouseDown={(event) => event.target === event.currentTarget && closeCreate()}><form className="organization-create-drawer" onSubmit={handleCreate}>
        <header><div><span>创建校园群体</span><h2>{createStep === 1 ? "这个群体用来做什么？" : createStep === 2 ? "填写基本信息" : createStep === 3 ? "设置加入与权限" : "确认创建内容"}</h2></div><button type="button" onClick={closeCreate} aria-label="关闭创建群体">×</button></header>
        <div className="organization-create-progress" aria-label={`第 ${createStep} 步，共 4 步`}>{[1, 2, 3, 4].map((step) => <span key={step} className={step <= createStep ? "is-active" : ""} />)}</div>
        <div className="organization-create-content">
          {createStep === 1 && <><div className="organization-create-types">{CREATE_TYPES.map((item) => <button key={item.id} type="button" className={createType === item.id ? "is-selected" : ""} onClick={() => setCreateType(item.id)}><span>{item.icon}</span><div><strong>{item.title}</strong><small>{item.note}</small></div><i>✓</i></button>)}</div><aside className="organization-official-tip"><strong>官方组织由学校统一维护</strong><p>学院、专业、班级、课程和寝室不能自行创建；关系有误时应提交组织变更申请。</p></aside></>}
          {createStep === 2 && <div className="organization-create-fields"><label><span>群体名称</span><input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder={`例如：${selectedCreateType.title}名称`} required /></label><label><span>群体简介</span><textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="说明群体目标、参与方式与希望共同完成的事情" rows={5} /></label><label><span>所属组织</span><select value={parentId} onChange={(event) => setParentId(event.target.value)}><option value="">暂不关联上级组织</option>{possibleParents.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label></div>}
          {createStep === 3 && <div className="organization-create-fields"><label><span>加入方式</span><select value={joinPolicy} onChange={(event) => setJoinPolicy(event.target.value)}><option value="APPROVAL">申请后由负责人审核</option><option value="OPEN">校内成员开放加入</option><option value="INVITE_ONLY">仅邀请加入</option><option value="CLOSED">暂不接受新成员</option></select></label><label><span>成员可见范围</span><select value={visibility} onChange={(event) => setVisibility(event.target.value)}><option value="MEMBERS_ONLY">仅成员可查看详情</option><option value="PUBLIC">校内公开</option><option value="PRIVATE">仅受邀成员可见</option></select></label><label><span>成员容量</span><input type="number" min="1" max="5000" value={capacity} onChange={(event) => setCapacity(event.target.value)} placeholder="例如：50" /></label><aside className="organization-permission-tip"><strong>角色与责任</strong><p>你将成为负责人，可添加管理员、普通成员和观察成员；成员审核和正式发布仍由负责人确认。</p></aside></div>}
          {createStep === 4 && <div className="organization-create-review"><span className="organization-avatar is-amber">{selectedCreateType.icon}</span><h3>{name || "未命名群体"}</h3><p>{description || selectedCreateType.note}</p><dl><div><dt>群体类型</dt><dd>{selectedCreateType.title}</dd></div><div><dt>所属组织</dt><dd>{possibleParents.find((org) => org.id === parentId)?.name ?? "暂不关联"}</dd></div><div><dt>加入方式</dt><dd>{joinPolicyLabel(joinPolicy)}</dd></div><div><dt>成员容量</dt><dd>{capacity || "不限"} 人</dd></div></dl><aside><strong>创建后仍由你确认关键操作</strong><p>群体 Agent 可以整理公开信息和辅助协作，但不能替代负责人作出成员管理与正式发布决定。</p></aside></div>}
          {createError && <p className="organization-create-error">{createError}</p>}
        </div>
        <footer><small>第 {createStep} 步，共 4 步</small><div>{createStep > 1 && <button type="button" onClick={() => setCreateStep((step) => step - 1)}>上一步</button>}<button className="is-primary" type="submit" disabled={creating || (createStep >= 2 && !name.trim())}>{creating ? "创建中…" : createStep === 4 ? "确认创建" : "继续"}</button></div></footer>
      </form></div>}
    </>
  );
}

export default function OrganizationsPage() {
  return <AppShell requireAuth><OrganizationsContent /></AppShell>;
}
