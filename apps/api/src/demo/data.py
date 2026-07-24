"""P11-01: Centralised demo data schema and constants.

Single source of truth for demo data shared by seed, reset, tests,
scripts, and documentation.

Privacy:
- Every record is fictional. No real personal data is used.
- DEMO_PASSWORD is a public demo-only constant; it must NEVER be
  written into Settings defaults or used as a production secret.
- DEMO_PRIVATE_PHRASE is a unique marker used by privacy E2E tests
  to prove private preference bodies never leak into results, admin
  pages, audit logs, browser storage, or URLs.
- Demo emails share the @example.com domain and a demo_ prefix so
  reset can identify the demo namespace without touching non-demo rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Namespace and shared constants
DEMO_NAMESPACE = "demo"
DEMO_EMAIL_DOMAIN = "example.com"
DEMO_PASSWORD = "CampusAgentDemo2026!"
DEMO_PRIVATE_PHRASE = "DEMO_PRIVATE_PHRASE_DO_NOT_RENDER"
DEMO_SCENE_IDEMPOTENCY_KEY = "demo-dorm-dinner-scene-v1"
DEMO_ORG_SLUG_SUFFIX = "-demo-lab"


def _demo_email(local: str) -> str:
    return f"{local}@{DEMO_EMAIL_DOMAIN}"


@dataclass(frozen=True)
class DemoUser:
    """A fictional demo user."""

    key: str
    email: str
    display_name: str
    student_no: str
    major_name: str
    enrollment_year: int
    global_role: str
    status: str = "ACTIVE"
    soft_deleted: bool = False
    bio: str = ""

    @property
    def is_admin(self) -> bool:
        return self.global_role == "SYSTEM_ADMIN"


_ROLE_SYSTEM_ADMIN = "SYSTEM_ADMIN"
_ROLE_STUDENT = "STUDENT"
_STATUS_ACTIVE = "ACTIVE"
_STATUS_DELETED = "DELETED"

DEMO_ADMIN = DemoUser(
    key="admin",
    email=_demo_email("demo_admin"),
    display_name="Demo Admin",
    student_no="D20260001",
    major_name="Educational Administration",
    enrollment_year=2022,
    global_role=_ROLE_SYSTEM_ADMIN,
    status=_STATUS_ACTIVE,
    bio="Demo lab administrator (fictional).",
)

DEMO_ALICE = DemoUser(
    key="alice",
    email=_demo_email("demo_alice"),
    display_name="Alice Chen",
    student_no="S20261001",
    major_name="Computer Science",
    enrollment_year=2026,
    global_role=_ROLE_STUDENT,
    status=_STATUS_ACTIVE,
    bio="Demo student in Dorm 301 (fictional).",
)

DEMO_BOB = DemoUser(
    key="bob",
    email=_demo_email("demo_bob"),
    display_name="Bob Lin",
    student_no="S20261002",
    major_name="Software Engineering",
    enrollment_year=2026,
    global_role=_ROLE_STUDENT,
    status=_STATUS_ACTIVE,
    bio="Demo student in Dorm 301 (fictional).",
)

DEMO_CAROL = DemoUser(
    key="carol",
    email=_demo_email("demo_carol"),
    display_name="Carol Wang",
    student_no="S20261003",
    major_name="Data Science",
    enrollment_year=2026,
    global_role=_ROLE_STUDENT,
    status=_STATUS_ACTIVE,
    bio="Demo student in Dorm 301 (fictional).",
)

DEMO_DELETED = DemoUser(
    key="deleted",
    email=_demo_email("demo_deleted"),
    display_name="Deleted Demo User",
    student_no="S20260999",
    major_name="General Studies",
    enrollment_year=2024,
    global_role=_ROLE_STUDENT,
    status=_STATUS_DELETED,
    soft_deleted=True,
    bio="Demo account that has been soft-deleted (fictional).",
)

DEMO_USERS: list[DemoUser] = [
    DEMO_ADMIN,
    DEMO_ALICE,
    DEMO_BOB,
    DEMO_CAROL,
    DEMO_DELETED,
]

DEMO_USERS_BY_KEY: dict[str, DemoUser] = {u.key: u for u in DEMO_USERS}
DEMO_SCENE_PARTICIPANT_KEYS: list[str] = ["alice", "bob", "carol"]


@dataclass(frozen=True)
class DemoOrganization:
    key: str
    name: str
    slug: str
    type: str
    parent_key: str | None
    description: str
    visibility: str = "PUBLIC"
    join_policy: str = "INVITE_ONLY"


DEMO_SCHOOL = DemoOrganization(
    key="school",
    name="信息科学技术学院",
    slug="jnu-campus" + DEMO_ORG_SLUG_SUFFIX,
    type="COLLEGE",
    parent_key=None,
    description="暨南大学信息科学技术学院官方组织空间。",
    join_policy="CLOSED",
)

DEMO_PROJECT = DemoOrganization(
    key="project",
    name="Campus Agent",
    slug="campus-agent-project" + DEMO_ORG_SLUG_SUFFIX,
    type="TEAM",
    parent_key=None,
    description="Campus Agent 项目交流、任务协作与共同建设空间。",
    visibility="MEMBERS_ONLY",
    join_policy="APPROVAL",
)

DEMO_LAB = DemoOrganization(
    key="lab",
    name="WNDS实验室",
    slug="wnds-lab" + DEMO_ORG_SLUG_SUFFIX,
    type="LAB",
    parent_key=None,
    description="模型互联网与智能系统研究、讨论和项目协作空间。",
    visibility="MEMBERS_ONLY",
    join_policy="INVITE_ONLY",
)

DEMO_CLUB = DemoOrganization(
    key="club",
    name="模型互联网",
    slug="model-internet-club" + DEMO_ORG_SLUG_SUFFIX,
    type="CLUB",
    parent_key=None,
    description="面向暨南大学学生的模型互联网兴趣交流与实践社团。",
    join_policy="APPROVAL",
)

DEMO_COURSE = DemoOrganization(
    key="course",
    name="人工智能",
    slug="artificial-intelligence-course" + DEMO_ORG_SLUG_SUFFIX,
    type="COURSE",
    parent_key=None,
    description="人工智能课程通知、学习资料和课程协作空间。",
    visibility="MEMBERS_ONLY",
    join_policy="CLOSED",
)

DEMO_DORM = DemoOrganization(
    key="dorm",
    name="东9 T207",
    slug="demo-dorm-301" + DEMO_ORG_SLUG_SUFFIX,
    type="DORM",
    parent_key=None,
    description="东9栋 T207 寝室生活、公共事项与日常协商群体。",
    visibility="PRIVATE",
    join_policy="CLOSED",
)

DEMO_DISCOVER_ORGANIZATIONS: list[DemoOrganization] = [
    DemoOrganization(
        key="discover_open_source",
        name="暨南大学开源软件社区",
        slug="jnu-open-source" + DEMO_ORG_SLUG_SUFFIX,
        type="CLUB",
        parent_key=None,
        description="面向全校学生的开源项目交流、贡献与实践社区。",
        join_policy="OPEN",
    ),
    DemoOrganization(
        key="discover_llm_reading",
        name="大模型技术读书会",
        slug="llm-reading" + DEMO_ORG_SLUG_SUFFIX,
        type="OTHER",
        parent_key=None,
        description="共同阅读大模型、智能体与模型互联网方向的论文和技术资料。",
        join_policy="APPROVAL",
    ),
    DemoOrganization(
        key="discover_cv",
        name="计算机视觉学习小组",
        slug="computer-vision-study" + DEMO_ORG_SLUG_SUFFIX,
        type="TEAM",
        parent_key=None,
        description="围绕视觉识别、多模态学习与工程实践开展学习协作。",
        join_policy="OPEN",
    ),
    DemoOrganization(
        key="discover_math",
        name="数学建模竞赛队",
        slug="math-modeling-team" + DEMO_ORG_SLUG_SUFFIX,
        type="TEAM",
        parent_key=None,
        description="数学建模训练、组队和竞赛信息共享群体。",
        join_policy="APPROVAL",
    ),
    DemoOrganization(
        key="discover_challenge",
        name="挑战杯项目共创组",
        slug="challenge-cup" + DEMO_ORG_SLUG_SUFFIX,
        type="TEAM",
        parent_key=None,
        description="面向挑战杯项目的选题讨论、成员匹配与材料共创。",
        join_policy="APPROVAL",
    ),
    DemoOrganization(
        key="discover_gba",
        name="粤港澳大湾区创新实践社",
        slug="gba-innovation" + DEMO_ORG_SLUG_SUFFIX,
        type="CLUB",
        parent_key=None,
        description="关注湾区产业、创新创业和跨校实践机会。",
        join_policy="APPROVAL",
    ),
    DemoOrganization(
        key="discover_volunteer",
        name="番禺校区志愿服务队",
        slug="panyu-volunteer" + DEMO_ORG_SLUG_SUFFIX,
        type="CLUB",
        parent_key=None,
        description="发布校内志愿服务、公益活动和岗位排班。",
        join_policy="OPEN",
    ),
    DemoOrganization(
        key="discover_photo",
        name="校园摄影协会",
        slug="campus-photo" + DEMO_ORG_SLUG_SUFFIX,
        type="CLUB",
        parent_key=None,
        description="校园影像记录、摄影交流与活动拍摄协作。",
        join_policy="OPEN",
    ),
    DemoOrganization(
        key="discover_badminton",
        name="周末羽毛球约练群",
        slug="weekend-badminton" + DEMO_ORG_SLUG_SUFFIX,
        type="OTHER",
        parent_key=None,
        description="面向校内成员的周末羽毛球约练和场地协调群体。",
        join_policy="OPEN",
    ),
    DemoOrganization(
        key="discover_english",
        name="英语交流角",
        slug="english-corner" + DEMO_ORG_SLUG_SUFFIX,
        type="OTHER",
        parent_key=None,
        description="英语口语练习、主题分享和跨文化交流群体。",
        join_policy="OPEN",
    ),
    DemoOrganization(
        key="discover_freshman",
        name="新生校园互助群",
        slug="freshman-help" + DEMO_ORG_SLUG_SUFFIX,
        type="OTHER",
        parent_key=None,
        description="帮助新同学了解课程、校园服务和日常生活。",
        join_policy="APPROVAL",
    ),
    DemoOrganization(
        key="discover_academic",
        name="研究生学术交流组",
        slug="graduate-academic" + DEMO_ORG_SLUG_SUFFIX,
        type="TEAM",
        parent_key=None,
        description="跨方向学术报告、论文交流和科研经验分享群体。",
        join_policy="INVITE_ONLY",
    ),
]

DEMO_ORGANIZATIONS: list[DemoOrganization] = [
    DEMO_PROJECT,
    DEMO_LAB,
    DEMO_SCHOOL,
    DEMO_CLUB,
    DEMO_COURSE,
    DEMO_DORM,
    *DEMO_DISCOVER_ORGANIZATIONS,
]
DEMO_ORGANIZATIONS_BY_KEY: dict[str, DemoOrganization] = {o.key: o for o in DEMO_ORGANIZATIONS}


@dataclass(frozen=True)
class DemoMembership:
    user_key: str
    org_key: str
    role: str
    status: str = "ACTIVE"


DEMO_MEMBERSHIPS: list[DemoMembership] = [
    DemoMembership(user_key="admin", org_key="school", role="OWNER"),
    DemoMembership(user_key="admin", org_key="project", role="ADMIN"),
    DemoMembership(user_key="admin", org_key="lab", role="ADMIN"),
    DemoMembership(user_key="admin", org_key="club", role="ADMIN"),
    DemoMembership(user_key="admin", org_key="course", role="ADMIN"),
    DemoMembership(user_key="admin", org_key="dorm", role="ADMIN"),
    DemoMembership(user_key="alice", org_key="project", role="OWNER"),
    DemoMembership(user_key="alice", org_key="lab", role="OWNER"),
    DemoMembership(user_key="alice", org_key="school", role="MEMBER"),
    DemoMembership(user_key="alice", org_key="club", role="MEMBER"),
    DemoMembership(user_key="alice", org_key="course", role="MEMBER"),
    DemoMembership(user_key="alice", org_key="dorm", role="MEMBER"),
    DemoMembership(user_key="bob", org_key="dorm", role="MEMBER"),
    DemoMembership(user_key="carol", org_key="dorm", role="MEMBER"),
]


@dataclass(frozen=True)
class DemoConversation:
    key: str
    title: str
    type: str = "GROUP"
    participant_keys: list[str] = field(default_factory=list)


DEMO_CONVERSATION = DemoConversation(
    key="dorm-chat",
    title="东9 T207 寝室群聊",
    type="GROUP",
    participant_keys=["alice", "bob", "carol"],
)

# A few seed chat messages (non-sensitive, public text only).
DEMO_MESSAGES: list[dict[str, Any]] = [
    {
        "sender_key": "alice",
        "message_type": "TEXT",
        "content": "Shall we have dinner together tonight?",
    },
    {
        "sender_key": "bob",
        "message_type": "TEXT",
        "content": "Sounds good, I will submit my preferences.",
    },
    {
        "sender_key": "carol",
        "message_type": "TEXT",
        "content": "Me too. Submitting mine next.",
    },
]


# Demo private preferences for the dorm-dinner scene.
# Each participant has a private body that carries DEMO_PRIVATE_PHRASE
# so privacy E2E can detect any leak across results/admin/storage/URL.
def _make_dinner_prefs(
    *,
    budget_min: int,
    budget_max: int,
    cuisines: list[str],
    dietary: list[str],
    distance: str,
    time_slots: list[str],
    environment: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "budget_min": budget_min,
        "budget_max": budget_max,
        "cuisine_preferences": cuisines,
        "dietary_restrictions": dietary,
        "distance_preference": distance,
        "available_time": time_slots,
        "environment_preference": environment,
        "notes": notes,
    }


DEMO_ALICE_PREFERENCES = _make_dinner_prefs(
    budget_min=25,
    budget_max=60,
    cuisines=["sichuan", "hotpot"],
    dietary=["none"],
    distance="moderate",
    time_slots=["dinner"],
    environment="lively",
    notes=f"Alice private note: {DEMO_PRIVATE_PHRASE}",
)

DEMO_BOB_PREFERENCES = _make_dinner_prefs(
    budget_min=20,
    budget_max=50,
    cuisines=["northern", "cantonese"],
    dietary=["vegetarian"],
    distance="close",
    time_slots=["early_dinner", "dinner"],
    environment="quiet",
    notes=f"Bob private note: {DEMO_PRIVATE_PHRASE}",
)

DEMO_CAROL_PREFERENCES = _make_dinner_prefs(
    budget_min=30,
    budget_max=70,
    cuisines=["japanese", "korean"],
    dietary=["none"],
    distance="moderate",
    time_slots=["dinner"],
    environment="moderate",
    notes=f"Carol private note: {DEMO_PRIVATE_PHRASE}",
)

#: Preferences keyed by participant key.
DEMO_PREFERENCES_BY_PARTICIPANT: dict[str, dict[str, Any]] = {
    "alice": DEMO_ALICE_PREFERENCES,
    "bob": DEMO_BOB_PREFERENCES,
    "carol": DEMO_CAROL_PREFERENCES,
}

#: Demo votes — two APPROVE votes on the top-ranked candidate.
#: The candidate_id is resolved at seed time from the generated
#: SceneCandidate with rank=1.
DEMO_VOTES: list[dict[str, Any]] = [
    {"voter_key": "alice", "vote_value": "APPROVE"},
    {"voter_key": "bob", "vote_value": "APPROVE"},
]


# ---------------------------------------------------------------------------
# Model gateway mock node (P7) — a single deterministic mock provider.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DemoModelNode:
    key: str
    name: str
    provider_type: str = "MOCK"
    endpoint: str = "http://mock-model.local:8001"
    status: str = "ACTIVE"


DEMO_MODEL_NODE = DemoModelNode(
    key="mock-node",
    name="Demo Mock Model Node",
)

DEMO_MODEL_NODES: list[DemoModelNode] = [DEMO_MODEL_NODE]


def demo_emails() -> list[str]:
    """Return all demo user emails (lowercased)."""
    return [u.email for u in DEMO_USERS]


def is_demo_email(email: str) -> bool:
    """Return True if an email belongs to the demo namespace."""
    if not email:
        return False
    normalised = email.lower().strip()
    return normalised.startswith("demo_") and normalised.endswith(f"@{DEMO_EMAIL_DOMAIN}")


def is_demo_org_slug(slug: str) -> bool:
    """Return True if an org slug belongs to the demo namespace."""
    return bool(slug) and slug.endswith(DEMO_ORG_SLUG_SUFFIX)
