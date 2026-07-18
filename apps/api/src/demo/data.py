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
    name="JNU Campus Demo Lab",
    slug="jnu-campus" + DEMO_ORG_SLUG_SUFFIX,
    type="SCHOOL",
    parent_key=None,
    description="Fictional campus used for CampusAgent demos (P11).",
    join_policy="APPROVAL",
)

DEMO_DORM = DemoOrganization(
    key="dorm",
    name="Demo Dorm 301",
    slug="demo-dorm-301" + DEMO_ORG_SLUG_SUFFIX,
    type="DORM",
    parent_key="school",
    description="Fictional dormitory 301 for the dinner demo.",
    join_policy="OPEN",
)

DEMO_ORGANIZATIONS: list[DemoOrganization] = [DEMO_SCHOOL, DEMO_DORM]
DEMO_ORGANIZATIONS_BY_KEY: dict[str, DemoOrganization] = {
    o.key: o for o in DEMO_ORGANIZATIONS
}


@dataclass(frozen=True)
class DemoMembership:
    user_key: str
    org_key: str
    role: str
    status: str = "ACTIVE"


DEMO_MEMBERSHIPS: list[DemoMembership] = [
    DemoMembership(user_key="admin", org_key="school", role="OWNER"),
    DemoMembership(user_key="admin", org_key="dorm", role="ADMIN"),
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
    title="Demo Dorm 301 Group Chat",
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

