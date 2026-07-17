# P4 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P4「组织、成员与校园目录」完整执行指令。执行方必须在 `/root/CampusAgent` 中按任务顺序完成 P4-01～P4-12；不得跳任务、不得执行 P5+、不得提交、不得推送。完成后输出完整报告，交给 Codex 做全量审计、修复、提交和远端 CI 观察。
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans if available. Implement task-by-task, keep each task independently testable, and update the checkbox-style logs as work progresses.

## 0. 项目背景

项目名称：CampusAgent

项目定位：隐私优先、智能体原生的校园平台。系统面向校园组织、师生、社团、活动与多智能体协作场景，核心能力包括 Conversation、Agent、Memory、Scene、Model Gateway、Admin、Edge Node、WebSocket 实时事件和隐私测试矩阵。

项目路径：

```text
/root/CampusAgent
```

远程仓库：

```text
git@github.com:SWFann/CampusAgent.git
```

当前分支：

```text
main
```

当前基准提交：

```text
34df5d5 test(auth): avoid gitleaks false positive in auth model test
```

P3 收口提交：

```text
3c423e5 feat(auth): complete P3 identity and session security
34df5d5 test(auth): avoid gitleaks false positive in auth model test
```

P3 远端 CI：

```text
https://github.com/SWFann/CampusAgent/actions/runs/29512607770
```

P3 CI 状态：

- `Lint, Typecheck & Test`: success
- `E2E Tests (Playwright)`: success

当前环境：

- 后续开发统一以 `/root/CampusAgent` 为准。
- Python 环境优先使用 conda 环境 `CampusAgent`。
- Docker 在本机 WSL 内可能不可用；如果 `docker command not found`，记录原因，但不要跳过非 Docker 验证。
- `gh` CLI 可能不可用；远端 CI 由 Codex 后续观察。
- P4 执行方不得提交、不得推送。

## 1. 当前权威状态

P0/P1 权威口径：

- HTTP API 契约：`v1.0-frozen`
- HTTP API 端点：68 个 MVP + 3 个 internal = 71 个总文档化端点
- WebSocket 契约：`v1.0-frozen`
- 威胁模型：T-01～T-09，共 9 个威胁
- 风险分布：严重 1 / 高 6 / 中 2 / 低 0
- 控制状态：`planned=9 / implemented=0 / verified=0`
- 隐私测试：`defined=100 / not_run=100`

P2 已完成：

- Docker Compose 基线
- Settings 配置对象
- PostgreSQL engine/session
- Alembic 基线迁移
- Redis 客户端
- API Envelope
- 请求上下文中间件
- 敏感日志过滤
- Clock/UUID 工具
- 领域事件总线
- Repository / Unit of Work 基线
- 测试数据库夹具
- OpenAPI 基线
- 基础可观测性

P3 已完成：

- `User`、`StudentProfile`、`AuthSession`、`RefreshToken`
- 密码哈希、强度校验、统一认证失败响应
- 注册、登录、刷新、注销、`/auth/me`
- JWT + HttpOnly Cookie + CSRF double-submit
- Refresh token 轮换、重放检测、family 撤销
- 软删除账号和会话撤销
- 进程内 Auth 限流
- `UserRegistered` 领域事件
- 登录和注册前端页面

P4 当前状态：

- `apps/api/src/modules/organizations/` 仍主要是 P1 骨架。
- `apps/api/src/modules/directory/` 仍主要是 P1 骨架。
- P3 中 `GET /api/v1/users/{user_id}/organizations` 仍是占位/空逻辑，P4 必须改成真实实现。

## 2. 必读文件

开始前必须阅读：

1. `docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md`
2. `docs/project/README.md`
3. `docs/development/DEVELOPMENT_PLAN.md`
4. `docs/development/P3-COMPLETION-REPORT.md`
5. `docs/development/P3_FULL_IMPLEMENTATION_GUIDE.md`
6. `docs/api/API_CONTRACT.md`
7. `docs/api/WEBSOCKET_CONTRACT.md`
8. `docs/api/MVP_ENDPOINT_TRACEABILITY.md`
9. `docs/domain/DOMAIN_VOCABULARY.md`
10. `docs/architecture/PERMISSION_MATRIX.md`
11. `docs/privacy/PRIVACY_TEST_MATRIX.md`
12. `docs/security/THREAT_MODEL.md`
13. `apps/api/src/config.py`
14. `apps/api/src/main.py`
15. `apps/api/src/dependencies.py`
16. `apps/api/src/db/base.py`
17. `apps/api/src/db/session.py`
18. `apps/api/src/events/bus.py`
19. `apps/api/src/schemas/envelope.py`
20. `apps/api/src/modules/auth/dependencies.py`
21. `apps/api/src/modules/auth/csrf.py`
22. `apps/api/src/modules/users/models.py`
23. `apps/api/src/modules/users/service.py`
24. `apps/api/src/modules/users/api.py`
25. `apps/api/tests/conftest.py`
26. `apps/web/src/lib/api.ts`
27. `apps/web/src/lib/csrf.ts`

阅读后先确认：

```bash
cd /root/CampusAgent
git status --short --branch
git log -3 --oneline
```

预期：

- 当前分支为 `main`。
- 工作树干净。
- 最新提交为 `34df5d5 test(auth): avoid gitleaks false positive in auth model test`。

如果工作树不干净：

- 停止实现。
- 记录 `git status --short --branch`。
- 不要回滚、不覆盖、不删除用户或 Codex 现有修改。

## 3. P4 总目标

P4 阶段名称：组织、成员与校园目录。

P4 总目标：

- 建立学校、学院、系、班级、宿舍、社团、课程、小组等组织底座。
- 实现组织 CRUD。
- 实现成员生命周期：邀请、加入、退出、移除、角色变更、状态转换。
- 严格区分全局角色和组织内角色。
- 实现组织权限策略：OWNER / ADMIN / MEMBER / GUEST。
- 保护最后一个 OWNER。
- 实现加入策略：OPEN / APPROVAL / INVITE_ONLY / CLOSED。
- 实现目录搜索、组织树和推荐占位规则。
- 发布组织和成员领域事件。
- 完成越权测试矩阵。
- 完成基础组织与联系人前端页面。

P4 完成后必须满足：

- 所有组织动作由权限服务判定。
- 搜索不返回隐藏资料。
- 组织树按当前用户权限裁剪。
- 组织成员变化有领域事件。
- 前端不会展示无权操作入口。
- 后端仍强制权限，不依赖前端隐藏按钮。
- 组织/目录接口返回统一 API Envelope。
- 写端点全部要求认证 + CSRF。
- P4 不实现 P5 聊天、P6 Agent、P7 模型网关等业务。

## 4. 冻结契约边界

禁止修改以下文件的语义：

- `docs/api/API_CONTRACT.md`
- `docs/api/WEBSOCKET_CONTRACT.md`
- `docs/architecture/PERMISSION_MATRIX.md`
- `docs/privacy/PRIVACY_TEST_MATRIX.md`
- `docs/security/THREAT_MODEL.md`

可以读取这些文件作为实现依据。

如果发现实现与冻结契约冲突：

1. 优先遵守冻结契约。
2. 在 P4 完成报告中记录冲突位置、处理方式和剩余风险。
3. 不擅自修改冻结契约。

P4 必须对齐的 API 契约重点：

- `POST /api/v1/organizations`
- `GET /api/v1/organizations`
- `GET /api/v1/organizations/{organization_id}`
- `PATCH /api/v1/organizations/{organization_id}`
- `DELETE /api/v1/organizations/{organization_id}`
- `POST /api/v1/organizations/{organization_id}/members`
- `GET /api/v1/organizations/{organization_id}/members`
- `PATCH /api/v1/organizations/{organization_id}/members/{user_id}`
- `DELETE /api/v1/organizations/{organization_id}/members/{user_id}`
- `POST /api/v1/organizations/{organization_id}/join`
- `POST /api/v1/organizations/{organization_id}/leave`
- `GET /api/v1/users/{user_id}/organizations`
- `GET /api/v1/directory/search`
- `GET /api/v1/directory/tree`
- `GET /api/v1/directory/recommended`

P4 必须对齐的错误码重点：

- `ORG_PERMISSION_DENIED`
- `ORG_NOT_FOUND`
- `ORG_MEMBER_ALREADY_EXISTS`
- `ORG_LAST_OWNER_CANNOT_LEAVE`
- `ORG_INVALID_JOIN_POLICY`
- `ORG_CAPACITY_EXCEEDED`
- `DIRECTORY_QUERY_TOO_SHORT`
- `DIRECTORY_INVALID_TYPE`
- `DIRECTORY_ORG_NOT_FOUND`
- `DIRECTORY_TREE_TOO_DEEP`
- `CSRF_TOKEN_MISSING`
- `CSRF_TOKEN_MISMATCH`

## 5. 执行方式

必须按顺序执行：

1. P4-01 设计组织模型
2. P4-02 实现组织 CRUD
3. P4-03 实现成员生命周期
4. P4-04 实现组织角色
5. P4-05 保护最后一个 Owner
6. P4-06 实现加入策略
7. P4-07 实现目录搜索
8. P4-08 实现组织树
9. P4-09 实现推荐占位规则
10. P4-10 发布成员领域事件
11. P4-11 完成越权测试矩阵
12. P4-12 完成组织与联系人页面

每个子任务完成时必须：

- 创建或更新对应 development log。
- 增加或更新测试。
- 跑该任务相关测试。
- 不提交。
- 不推送。
- 当前任务自检通过后再进入下一任务。

如果某个任务阻塞：

- 停止继续后续任务。
- 写清阻塞原因。
- 不要绕过。
- 不要靠删除测试通过。

## 6. 文件结构规划

后端需要实现或重写：

```text
apps/api/src/modules/organizations/models.py
apps/api/src/modules/organizations/schemas.py
apps/api/src/modules/organizations/repository.py
apps/api/src/modules/organizations/service.py
apps/api/src/modules/organizations/permissions.py
apps/api/src/modules/organizations/events.py
apps/api/src/modules/organizations/exceptions.py
apps/api/src/modules/organizations/api.py
```

后端需要实现或重写：

```text
apps/api/src/modules/directory/schemas.py
apps/api/src/modules/directory/service.py
apps/api/src/modules/directory/exceptions.py
apps/api/src/modules/directory/api.py
```

后端需要修改：

```text
apps/api/src/main.py
apps/api/src/modules/users/api.py
apps/api/src/modules/users/service.py
apps/api/tests/conftest.py
apps/api/tests/unit/test_alembic.py
```

新增迁移：

```text
apps/api/alembic/versions/0003_organization_membership_tables.py
```

新增或修改测试：

```text
apps/api/tests/unit/test_organization_models.py
apps/api/tests/unit/test_organization_crud.py
apps/api/tests/unit/test_organization_membership.py
apps/api/tests/unit/test_organization_permissions.py
apps/api/tests/unit/test_organization_join_policy.py
apps/api/tests/unit/test_organization_owner_protection.py
apps/api/tests/unit/test_organization_events.py
apps/api/tests/unit/test_directory_search.py
apps/api/tests/unit/test_directory_tree.py
apps/api/tests/unit/test_directory_recommended.py
apps/api/tests/unit/test_users_organizations.py
apps/api/tests/integration/test_organization_flow.py
```

前端建议新增：

```text
apps/web/src/app/organizations/page.tsx
apps/web/src/app/organizations/[organizationId]/page.tsx
apps/web/src/app/directory/page.tsx
apps/web/src/lib/organizations.ts
apps/web/src/lib/directory.ts
```

文档和日志必须新增：

```text
docs/development/P4-COMPLETION-REPORT.md
development-logs/in-progress/P4-01-organization-model.md
development-logs/in-progress/P4-02-organization-crud.md
development-logs/in-progress/P4-03-membership-lifecycle.md
development-logs/in-progress/P4-04-organization-roles.md
development-logs/in-progress/P4-05-last-owner-protection.md
development-logs/in-progress/P4-06-join-policy.md
development-logs/in-progress/P4-07-directory-search.md
development-logs/in-progress/P4-08-directory-tree.md
development-logs/in-progress/P4-09-directory-recommended.md
development-logs/in-progress/P4-10-membership-events.md
development-logs/in-progress/P4-11-authorization-test-matrix.md
development-logs/in-progress/P4-12-organization-frontend.md
```

文档必须修改：

```text
docs/development/DEVELOPMENT_PLAN.md
```

## 7. 数据模型设计

### 7.1 Organization

在 `apps/api/src/modules/organizations/models.py` 中实现。

推荐枚举：

```python
from enum import StrEnum

class OrganizationType(StrEnum):
    SCHOOL = "SCHOOL"
    COLLEGE = "COLLEGE"
    DEPARTMENT = "DEPARTMENT"
    CLASS = "CLASS"
    DORM = "DORM"
    CLUB = "CLUB"
    COURSE = "COURSE"
    TEAM = "TEAM"
    OTHER = "OTHER"

class OrganizationVisibility(StrEnum):
    PUBLIC = "PUBLIC"
    MEMBERS_ONLY = "MEMBERS_ONLY"
    PRIVATE = "PRIVATE"

class OrganizationJoinPolicy(StrEnum):
    OPEN = "OPEN"
    APPROVAL = "APPROVAL"
    INVITE_ONLY = "INVITE_ONLY"
    CLOSED = "CLOSED"

class OrganizationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"
```

推荐字段：

```python
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(40), nullable=False, default=OrganizationVisibility.PUBLIC.value
    )
    join_policy: Mapped[str] = mapped_column(
        String(40), nullable=False, default=OrganizationJoinPolicy.INVITE_ONLY.value
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=OrganizationStatus.ACTIVE.value
    )
    capacity: Mapped[int | None] = mapped_column(nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

关系建议：

- `parent`
- `children`
- `memberships`
- `creator`

`__repr__` 要避免输出超长描述，不输出成员、用户敏感字段。

### 7.2 OrganizationMembership

推荐枚举：

```python
class OrganizationRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    GUEST = "GUEST"

class MembershipStatus(StrEnum):
    INVITED = "INVITED"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    LEFT = "LEFT"
    REMOVED = "REMOVED"
```

推荐字段：

```python
class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(
        String(40), nullable=False, default=OrganizationRole.MEMBER.value
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=MembershipStatus.ACTIVE.value
    )
    invited_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )
```

约束：

- 唯一约束：`(organization_id, user_id)`。
- 一个组织只能有一个有效 OWNER；使用 service 层保护，避免 SQLite partial index 差异。
- 状态变化复用同一行，不为同一用户和组织创建多条当前权威 membership。

## 8. Alembic 迁移

新增：

```text
apps/api/alembic/versions/0003_organization_membership_tables.py
```

迁移要求：

- `revision = "0003_organization_membership_tables"`
- `down_revision = "0002_user_auth_tables"`
- 创建 `organizations`
- 创建 `organization_memberships`
- 创建索引：
  - `ix_organizations_parent_id`
  - `ix_organizations_type`
  - `ix_organizations_status`
  - `ix_organization_memberships_organization_id`
  - `ix_organization_memberships_user_id`
  - `ix_organization_memberships_role`
  - `ix_organization_memberships_status`
- 创建唯一约束：
  - `uq_organization_memberships_org_user`

必须更新：

```text
apps/api/tests/unit/test_alembic.py
```

必须测试：

- upgrade 后存在 `organizations`
- upgrade 后存在 `organization_memberships`
- downgrade 后表移除
- upgrade -> downgrade -> upgrade 可重复

## 9. Schema 设计

在 `organizations/schemas.py` 中定义：

- `OrganizationCreateRequest`
- `OrganizationUpdateRequest`
- `OrganizationRead`
- `OrganizationListItem`
- `OrganizationMemberAddRequest`
- `OrganizationMemberUpdateRequest`
- `OrganizationMemberRead`
- `OrganizationJoinResponse`
- `OrganizationListResponse`
- `OrganizationMembersResponse`

字段原则：

- 输入 schema 使用冻结契约字段名。
- 输出 schema 不包含内部权限计算细节，除非是安全字段。
- 不返回用户 email/student_no/password_hash/token/session。
- 成员列表用户字段只返回 `id`、`display_name`、`avatar_url`、`global_role` 可选，但不要返回 email。

在 `directory/schemas.py` 中定义：

- `DirectorySearchType`
- `DirectoryUserResult`
- `DirectoryOrganizationResult`
- `DirectorySearchResponse`
- `DirectoryTreeNode`
- `DirectoryTreeResponse`
- `DirectoryRecommendedResponse`

目录投影原则：

- 用户结果不得返回 email。
- 用户结果不得返回 student_no。
- 用户结果不得返回 private bio，除非 visibility 和权限允许；MVP 可统一不返回 bio。
- 组织结果根据 visibility 和权限过滤。

## 10. Exceptions 设计

在 `organizations/exceptions.py` 中实现 AppError 子类：

- `OrganizationNotFoundError` -> `ORG_NOT_FOUND`, 404
- `OrganizationPermissionDeniedError` -> `ORG_PERMISSION_DENIED`, 403
- `OrganizationMemberAlreadyExistsError` -> `ORG_MEMBER_ALREADY_EXISTS`, 409
- `OrganizationLastOwnerError` -> `ORG_LAST_OWNER_CANNOT_LEAVE`, 409
- `OrganizationInvalidJoinPolicyError` -> `ORG_INVALID_JOIN_POLICY`, 400
- `OrganizationCapacityExceededError` -> `ORG_CAPACITY_EXCEEDED`, 409

在 `directory/exceptions.py` 中实现：

- `DirectoryQueryTooShortError` -> `DIRECTORY_QUERY_TOO_SHORT`, 400
- `DirectoryInvalidTypeError` -> `DIRECTORY_INVALID_TYPE`, 400
- `DirectoryOrgNotFoundError` -> `DIRECTORY_ORG_NOT_FOUND`, 404
- `DirectoryTreeTooDeepError` -> `DIRECTORY_TREE_TOO_DEEP`, 400

所有异常必须继承 `src.utils.errors.AppError`，由 P2 全局 exception handler 输出统一 envelope。

## 11. Repository 设计

在 `organizations/repository.py` 中实现：

- `OrganizationRepository`
  - `get_by_id`
  - `get_active_by_id`
  - `list_active`
  - `get_children`
  - `slug_exists`
  - `count_active_members`
  - `search`
- `OrganizationMembershipRepository`
  - `get_by_org_user`
  - `get_active_by_org_user`
  - `list_active_by_org`
  - `list_active_by_user`
  - `count_active_owners`
  - `count_active_members`
  - `has_active_membership`

Repository 只做查询和基础持久化，不做权限决策。

权限、最后 OWNER、加入策略都必须在 service / permissions 中处理。

## 12. 权限策略

在 `organizations/permissions.py` 中实现集中权限服务。

建议接口：

```python
class OrganizationPermissionService:
    def can_view_organization(self, actor: User | None, organization: Organization, membership: OrganizationMembership | None) -> bool: ...
    def can_view_members(self, actor: User, organization: Organization, membership: OrganizationMembership | None) -> bool: ...
    def can_update_organization(self, actor: User, membership: OrganizationMembership | None) -> bool: ...
    def can_delete_organization(self, actor: User, membership: OrganizationMembership | None) -> bool: ...
    def can_add_member(self, actor: User, actor_membership: OrganizationMembership | None, target_role: str) -> bool: ...
    def can_remove_member(self, actor: User, actor_membership: OrganizationMembership | None, target_membership: OrganizationMembership) -> bool: ...
    def can_change_member_role(self, actor: User, actor_membership: OrganizationMembership | None, target_membership: OrganizationMembership, new_role: str) -> bool: ...
```

权限规则：

- 全局 `SYSTEM_ADMIN` 可管理全部组织。
- 全局 `SCHOOL_ADMIN` P4 MVP 可管理全部组织；必须在日志声明后续按学校范围收窄。
- 全局 `ORG_ADMIN` 不自动等于任意组织 OWNER。只有组织 membership 或后续管理范围配置后才可管理组织。
- `OWNER`：
  - 可查看组织。
  - 可查看成员。
  - 可更新组织。
  - 可归档/删除组织。
  - 可添加成员。
  - 可移除成员。
  - 可修改成员角色。
  - 可转让 OWNER。
- `ADMIN`：
  - 可查看组织。
  - 可查看成员。
  - 可更新组织的非敏感字段。
  - 可添加 MEMBER/GUEST。
  - 可移除 MEMBER/GUEST。
  - 可修改 MEMBER/GUEST。
  - 不可操作 OWNER。
  - 不可把任何人升为 OWNER。
- `MEMBER`：
  - 可查看组织。
  - 可查看成员。
  - 可退出组织。
  - 不可管理成员。
- `GUEST`：
  - 可查看组织最小信息。
  - 可退出组织。
  - 不可查看完整成员列表，除非契约另有要求；MVP 建议只读最小。
- 非成员：
  - 只能查看 PUBLIC 组织基础信息。
  - 不能查看 MEMBERS_ONLY/PRIVATE 组织详情。
  - 不能查看成员列表。

最后 OWNER 保护：

- 最后一个 OWNER 不能 leave。
- 最后一个 OWNER 不能被 remove。
- 最后一个 OWNER 不能被降级。
- 最后一个 OWNER 不能通过删除 membership 绕过。
- 如果删除组织采用软删除，必须由 OWNER 或 SYSTEM_ADMIN 执行，并在测试中证明不是成员删除绕过。

## 13. Service 设计

在 `organizations/service.py` 中实现业务逻辑。

建议函数：

- `create_organization`
- `list_organizations`
- `get_organization`
- `update_organization`
- `delete_organization`
- `add_member`
- `list_members`
- `update_member_role`
- `remove_member`
- `join_organization`
- `leave_organization`
- `list_user_organizations`

事务原则：

- 每个 service 函数接收 SQLAlchemy `Session`。
- service 负责 commit。
- 事件必须在 commit 成功后发布。
- 失败时 rollback 由 DB dependency 或 service 明确处理。
- 不在 API handler 中直接操作 ORM。

创建组织规则：

- 创建者必须是 authenticated user。
- 创建成功后自动创建 OWNER membership。
- 如果 `capacity` 非空且小于 1，返回 validation error 或业务错误。
- 如果 parent_id 存在，必须验证父组织存在且未删除。
- 如果 slug 重复，返回合适错误；冻结契约没有专用 `ORG_ALREADY_EXISTS`，MVP 可用 409 AppError 自定义 code 但需在报告中说明，或使用 validation error。

更新组织规则：

- 只有 OWNER / ADMIN / SYSTEM_ADMIN / SCHOOL_ADMIN 可更新。
- `type` 是否允许修改由 MVP 决策。建议允许 OWNER 修改 name/description/visibility/join_policy/capacity，不允许修改 id/created_by/status。

删除组织规则：

- 使用软删除：`status=DELETED`、`deleted_at=utc_now()`。
- 或归档：`status=ARCHIVED`、`archived_at=utc_now()`。如果 API 是 DELETE，建议软删除。
- 删除后 search/list/tree 不返回该组织。

成员添加规则：

- OWNER 可添加 OWNER/ADMIN/MEMBER/GUEST，但添加 OWNER 时必须处理原 OWNER 转让或拒绝多 OWNER。
- ADMIN 只能添加 MEMBER/GUEST。
- MVP 建议：一个组织只允许一个 OWNER；如添加 OWNER，则必须先把旧 OWNER 降为 ADMIN，或者拒绝并要求用角色变更接口。需要测试和报告写清。
- 如果 target user 不存在或已删除，返回 USER_NOT_FOUND 或 NOT_FOUND，与现有 users 错误体系对齐。
- 如果 membership 已存在且 ACTIVE/PENDING/INVITED，返回 `ORG_MEMBER_ALREADY_EXISTS`。
- 如果 membership 为 LEFT/REMOVED，可以复用该行并恢复为 ACTIVE。

加入策略：

- OPEN：登录用户可直接 join，membership ACTIVE，role MEMBER。
- APPROVAL：登录用户 join 后 membership PENDING，role MEMBER。
- INVITE_ONLY：自助 join 返回 `ORG_INVALID_JOIN_POLICY` 或 `ORG_PERMISSION_DENIED`，按 API_CONTRACT 优先使用 `ORG_INVALID_JOIN_POLICY`。
- CLOSED：自助 join 返回 `ORG_INVALID_JOIN_POLICY`。
- capacity 满时返回 `ORG_CAPACITY_EXCEEDED`。

退出规则：

- 只有当前用户可 leave 自己。
- 最后 OWNER 不能 leave。
- leave 后 membership status = LEFT，left_at = utc_now()。

## 14. API 设计

在 `organizations/api.py` 中实现 APIRouter：

```python
router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])
```

所有写端点：

- `current_user: User = Depends(get_current_user)`
- `_csrf: None = Depends(require_csrf)`
- `db_session: Session = Depends(get_db_session)`
- `settings` 如需要

所有读端点：

- 公开列表可允许匿名，但若需要权限裁剪，使用可选用户依赖。P3 没有 optional current user 时，P4 可实现 `get_optional_current_user`，但不能破坏 `get_current_user`。
- 私有详情和成员列表必须认证。

响应统一：

- 使用 `src.schemas.envelope.success`
- request_id 使用 `request.state.request_id` 或项目现有 request context 字段。

在 `directory/api.py` 中实现：

```python
router = APIRouter(prefix="/api/v1/directory", tags=["directory"])
```

注册路由：

```python
from .modules.organizations.api import router as organizations_router
from .modules.directory.api import router as directory_router

application.include_router(organizations_router)
application.include_router(directory_router)
```

## 15. Users API 补齐

P4 必须修改 `apps/api/src/modules/users/api.py` 和 `users/service.py`。

`GET /api/v1/users/{user_id}/organizations` 要求：

- 若 user 不存在或 deleted，返回 not found。
- 若 actor 查询自己，返回自己的 ACTIVE membership 组织。
- 若 actor 查询别人，返回可公开组织：
  - PUBLIC organization 可以返回。
  - MEMBERS_ONLY 仅当 actor 与 target 共享该组织或 actor 有系统权限时返回。
  - PRIVATE 默认不返回，除非 actor 是同组织 OWNER/ADMIN/SYSTEM_ADMIN。
- 不返回 deleted/archived org。
- 不返回 target user email/student_no/password_hash。

必须测试：

- 查询自己有组织。
- 查询别人只返回 PUBLIC。
- PRIVATE 不泄露。
- deleted org 不返回。
- deleted user 返回 not found。

## 16. Directory 搜索

在 `directory/service.py` 中实现。

`GET /api/v1/directory/search` 参数建议：

- `q: str`
- `type: str = "all"`，允许 `all` / `users` / `organizations`
- `limit: int = 20`
- `cursor: str | None = None` 或简化 page/limit，按项目已有分页模式

规则：

- `q.strip()` 长度小于 2，返回 `DIRECTORY_QUERY_TOO_SHORT`。
- type 非法，返回 `DIRECTORY_INVALID_TYPE`。
- 用户搜索：
  - 搜索 display_name。
  - 不搜 email。
  - 不搜 student_no。
  - 不返回 email/student_no/password_hash。
  - DELETED/DISABLED 用户不返回。
- 组织搜索：
  - 搜索 name/slug。
  - PUBLIC 对所有人可见。
  - MEMBERS_ONLY 对成员可见。
  - PRIVATE 对成员或系统权限可见。
  - DELETED/ARCHIVED 不返回。
- 排序可简单按 name/display_name。
- 分页必须稳定，MVP 可用 limit + offset；如 API_CONTRACT 要 cursor，报告中说明 MVP 处理。

## 17. Directory Tree

`GET /api/v1/directory/tree` 参数建议：

- `root_organization_id: UUID | None`
- `max_depth: int = 3`

规则：

- max_depth 超过安全上限返回 `DIRECTORY_TREE_TOO_DEEP`。建议上限 5。
- root 不存在或 actor 无权查看，返回 `DIRECTORY_ORG_NOT_FOUND`。
- 返回树节点必须权限裁剪：
  - PUBLIC 节点可见。
  - MEMBERS_ONLY/PRIVATE 仅对成员或系统权限可见。
  - 子节点不可见时不返回。
- 不返回成员列表和敏感字段，只返回组织安全投影。

## 18. Directory Recommended

`GET /api/v1/directory/recommended`

MVP 推荐规则：

- 不做隐性画像。
- 不读取私有偏好。
- 不读取聊天、消息、记忆。
- 可基于当前用户已有组织关系返回：
  - 同 parent 下 PUBLIC 组织
  - 用户尚未加入的 PUBLIC CLUB/COURSE/TEAM
- 若无法安全推荐，返回空数组。
- 响应中必须包含可解释字段，如 `reason: "same_parent_public_organization"`。

必须测试：

- 未登录或无关系返回空或公开推荐。
- PRIVATE 组织不推荐给非成员。
- 不使用 email/student_no/bio 等敏感字段。

## 19. 领域事件

必须使用 P2 事件总线：

```python
from ...events.bus import DomainEvent, default_event_bus
```

不要在 `organizations/events.py` 中自定义另一个不兼容的 `DomainEvent`。

建议事件：

- `OrganizationCreated`
- `OrganizationArchived`
- `OrganizationMemberJoined`
- `OrganizationMemberLeft`
- `OrganizationMemberRoleChanged`

事件字段建议：

```python
@dataclass(frozen=True)
class OrganizationMemberJoined(DomainEvent):
    event_id: str
    organization_id: UUID
    user_id: UUID
    actor_id: UUID
    role: str
    occurred_at: datetime
```

隐私要求：

- 不包含 email。
- 不包含 student_no。
- 不包含 password/token/session。
- 不包含 private bio。
- 不包含组织私密描述以外的正文内容。MVP 建议事件只存 ID、role、status。

发布规则：

- service commit 成功后 publish。
- 测试事件只发布一次。
- 测试中使用 `default_event_bus.clear()` 或 fixture 隔离订阅者。

## 20. 前端 P4

P4-12 只做基础可用页面，不做完整 P10 App Shell。

新增：

```text
apps/web/src/app/organizations/page.tsx
apps/web/src/app/organizations/[organizationId]/page.tsx
apps/web/src/app/directory/page.tsx
apps/web/src/lib/organizations.ts
apps/web/src/lib/directory.ts
```

页面要求：

- `/organizations`
  - 组织列表。
  - 创建组织表单。
  - 显示 loading/error/empty。
- `/organizations/[organizationId]`
  - 组织详情。
  - 成员列表。
  - 添加成员表单。
  - 修改角色按钮。
  - 移除成员按钮。
  - 根据 API 返回权限状态隐藏无权操作入口。
- `/directory`
  - 搜索框。
  - 类型筛选：全部/用户/组织。
  - 搜索结果安全字段展示。
  - 推荐组织区域。

前端 API helper 要求：

- 所有请求 `credentials: "include"`。
- 写请求使用 `getWriteHeaders()` 带 CSRF。
- API base 使用 `NEXT_PUBLIC_API_URL`，延续 P3 `apps/web/src/lib/api.ts` 模式。
- 不使用 localStorage/sessionStorage 存 token。
- 不把 token 放 URL。

前端设计要求：

- 不做营销页。
- 直接进入可用工具界面。
- 保持简洁、密集、可扫描。
- 不用夸张 hero。
- 不用大量装饰渐变。

## 21. P4-01：设计组织模型

目标：

- 实现 `Organization`、`OrganizationMembership` ORM。
- 实现 0003 Alembic 迁移。
- 更新 conftest 导入模型。
- 更新 Alembic 测试。

Files:

- Modify: `apps/api/src/modules/organizations/models.py`
- Create: `apps/api/alembic/versions/0003_organization_membership_tables.py`
- Modify: `apps/api/tests/conftest.py`
- Modify: `apps/api/tests/unit/test_alembic.py`
- Create: `apps/api/tests/unit/test_organization_models.py`
- Create: `development-logs/in-progress/P4-01-organization-model.md`

最低测试：

- 创建 Organization 成功。
- 默认 visibility/join_policy/status 正确。
- parent-child 关系可用。
- 创建 OrganizationMembership 成功。
- `(organization_id, user_id)` 唯一。
- membership role/status 默认正确。
- repr 不泄露用户敏感字段。
- Alembic upgrade 创建两张表。
- Alembic downgrade 可回放。

任务完成后运行：

```bash
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_models.py apps/api/tests/unit/test_alembic.py -q -p no:cacheprovider
```

## 22. P4-02：实现组织 CRUD

目标：

- 实现组织创建、列表、详情、更新、软删除。
- 创建者自动成为 OWNER。
- 写端点要求认证 + CSRF。

Files:

- Modify: `apps/api/src/modules/organizations/schemas.py`
- Modify: `apps/api/src/modules/organizations/repository.py`
- Modify: `apps/api/src/modules/organizations/service.py`
- Modify: `apps/api/src/modules/organizations/exceptions.py`
- Modify: `apps/api/src/modules/organizations/api.py`
- Modify: `apps/api/src/main.py`
- Create: `apps/api/tests/unit/test_organization_crud.py`
- Create: `development-logs/in-progress/P4-02-organization-crud.md`

最低测试：

- 登录用户创建组织返回 201。
- 创建响应不包含敏感字段。
- 创建者自动成为 OWNER。
- 匿名创建返回 401。
- 缺 CSRF 创建返回 `CSRF_TOKEN_MISSING`。
- OWNER 可更新组织。
- MEMBER/非成员不可更新。
- OWNER 可软删除组织。
- 删除后列表/搜索不返回。
- 第二次删除返回 not found 或契约允许错误。

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_crud.py -q -p no:cacheprovider
```

## 23. P4-03：实现成员生命周期

目标：

- 实现成员添加、列表、角色更新、移除、加入、退出。
- 状态转换清晰：INVITED/PENDING/ACTIVE/LEFT/REMOVED。

Files:

- Modify: `apps/api/src/modules/organizations/schemas.py`
- Modify: `apps/api/src/modules/organizations/repository.py`
- Modify: `apps/api/src/modules/organizations/service.py`
- Modify: `apps/api/src/modules/organizations/api.py`
- Create: `apps/api/tests/unit/test_organization_membership.py`
- Create: `apps/api/tests/integration/test_organization_flow.py`
- Create: `development-logs/in-progress/P4-03-membership-lifecycle.md`

最低测试：

- OWNER 添加 MEMBER 成功。
- 重复添加返回 `ORG_MEMBER_ALREADY_EXISTS`。
- 成员列表只对有权用户可见。
- OWNER 移除 MEMBER 成功。
- 被移除用户不能继续查看 private organization。
- 用户 leave 后 membership status = LEFT。
- LEFT/REMOVED 用户重新加入按 join policy 恢复或创建，行为必须一致且有测试。

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_membership.py apps/api/tests/integration/test_organization_flow.py -q -p no:cacheprovider
```

## 24. P4-04：实现组织角色

目标：

- 建立集中权限策略。
- 覆盖 OWNER/ADMIN/MEMBER/GUEST/SYSTEM_ADMIN/SCHOOL_ADMIN/ORG_ADMIN。

Files:

- Modify: `apps/api/src/modules/organizations/permissions.py`
- Modify: `apps/api/src/modules/organizations/service.py`
- Create: `apps/api/tests/unit/test_organization_permissions.py`
- Create: `development-logs/in-progress/P4-04-organization-roles.md`

最低测试矩阵：

| Actor | View public | View private | Add member | Change role | Delete org |
|---|---:|---:|---:|---:|---:|
| anonymous | yes | no | no | no | no |
| non-member | yes | no | no | no | no |
| GUEST | yes | limited | no | no | no |
| MEMBER | yes | yes | no | no | no |
| ADMIN | yes | yes | yes, MEMBER/GUEST only | yes, MEMBER/GUEST only | no |
| OWNER | yes | yes | yes | yes | yes |
| SYSTEM_ADMIN | yes | yes | yes | yes | yes |
| ORG_ADMIN | no automatic power | no automatic power | no automatic power | no automatic power | no automatic power |

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_permissions.py -q -p no:cacheprovider
```

## 25. P4-05：保护最后一个 Owner

目标：

- 最后 OWNER 不能退出、被移除、被降级。
- 转让 OWNER 逻辑明确。

Files:

- Modify: `apps/api/src/modules/organizations/service.py`
- Modify: `apps/api/src/modules/organizations/permissions.py`
- Create: `apps/api/tests/unit/test_organization_owner_protection.py`
- Create: `development-logs/in-progress/P4-05-last-owner-protection.md`

最低测试：

- 最后 OWNER leave 返回 `ORG_LAST_OWNER_CANNOT_LEAVE`。
- 最后 OWNER remove 返回 `ORG_LAST_OWNER_CANNOT_LEAVE`。
- 最后 OWNER 降级返回 `ORG_LAST_OWNER_CANNOT_LEAVE`。
- 非最后 OWNER 可降级或移除，前提是仍有 OWNER。
- ADMIN 不能把自己或别人升为 OWNER。
- OWNER 转让后新 OWNER 生效，旧 OWNER 降为 ADMIN 或 MEMBER，行为必须测试并写入报告。

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_owner_protection.py -q -p no:cacheprovider
```

## 26. P4-06：实现加入策略

目标：

- OPEN / APPROVAL / INVITE_ONLY / CLOSED 行为明确。
- capacity 限制有效。

Files:

- Modify: `apps/api/src/modules/organizations/service.py`
- Modify: `apps/api/src/modules/organizations/api.py`
- Create: `apps/api/tests/unit/test_organization_join_policy.py`
- Create: `development-logs/in-progress/P4-06-join-policy.md`

最低测试：

- OPEN join -> ACTIVE MEMBER。
- APPROVAL join -> PENDING MEMBER。
- INVITE_ONLY join -> `ORG_INVALID_JOIN_POLICY`。
- CLOSED join -> `ORG_INVALID_JOIN_POLICY`。
- 已是成员 join -> `ORG_MEMBER_ALREADY_EXISTS`。
- capacity 满 join -> `ORG_CAPACITY_EXCEEDED`。
- 管理员添加成员也受 capacity 限制。

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_join_policy.py -q -p no:cacheprovider
```

## 27. P4-07：实现目录搜索

目标：

- 实现 `GET /api/v1/directory/search`。
- 用户/组织搜索字段投影安全。

Files:

- Modify: `apps/api/src/modules/directory/schemas.py`
- Modify: `apps/api/src/modules/directory/exceptions.py`
- Modify: `apps/api/src/modules/directory/service.py`
- Modify: `apps/api/src/modules/directory/api.py`
- Modify: `apps/api/src/main.py`
- Create: `apps/api/tests/unit/test_directory_search.py`
- Create: `development-logs/in-progress/P4-07-directory-search.md`

最低测试：

- query 长度小于 2 返回 `DIRECTORY_QUERY_TOO_SHORT`。
- invalid type 返回 `DIRECTORY_INVALID_TYPE`。
- 搜用户只返回 display_name/avatar/profile_visibility/id，不返回 email/student_no/password_hash。
- disabled/deleted user 不返回。
- PUBLIC organization 可被搜索。
- MEMBERS_ONLY/PRIVATE 对无权用户不返回。
- 成员可搜索到自己的 MEMBERS_ONLY/PRIVATE 组织。
- 搜索不读取或返回 P3/P4 私密正文。

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_directory_search.py -q -p no:cacheprovider
```

## 28. P4-08：实现组织树

目标：

- 实现 `GET /api/v1/directory/tree`。
- 按当前用户权限裁剪。

Files:

- Modify: `apps/api/src/modules/directory/schemas.py`
- Modify: `apps/api/src/modules/directory/service.py`
- Modify: `apps/api/src/modules/directory/api.py`
- Create: `apps/api/tests/unit/test_directory_tree.py`
- Create: `development-logs/in-progress/P4-08-directory-tree.md`

最低测试：

- 无 root 时返回 PUBLIC 根节点。
- 指定 root 返回子树。
- root 不存在返回 `DIRECTORY_ORG_NOT_FOUND`。
- max_depth 超限返回 `DIRECTORY_TREE_TOO_DEEP`。
- PRIVATE 子节点对非成员裁剪。
- MEMBERS_ONLY 子节点对成员可见。
- DELETED/ARCHIVED 节点不返回。

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_directory_tree.py -q -p no:cacheprovider
```

## 29. P4-09：实现推荐占位规则

目标：

- 实现 `GET /api/v1/directory/recommended`。
- 推荐只使用非敏感组织关系。
- 不做隐性画像。

Files:

- Modify: `apps/api/src/modules/directory/schemas.py`
- Modify: `apps/api/src/modules/directory/service.py`
- Modify: `apps/api/src/modules/directory/api.py`
- Create: `apps/api/tests/unit/test_directory_recommended.py`
- Create: `development-logs/in-progress/P4-09-directory-recommended.md`

最低测试：

- 未登录返回空推荐或仅 PUBLIC 推荐。
- 登录但无组织关系返回空推荐。
- 有组织关系时推荐同 parent 下 PUBLIC 组织。
- PRIVATE 不推荐给非成员。
- 推荐结果包含 reason。
- 不使用 email/student_no/bio/password_hash/token。

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_directory_recommended.py -q -p no:cacheprovider
```

## 30. P4-10：发布成员领域事件

目标：

- 发布组织创建和成员变更事件。
- 使用 P2 `default_event_bus`。

Files:

- Modify: `apps/api/src/modules/organizations/events.py`
- Modify: `apps/api/src/modules/organizations/service.py`
- Modify: `apps/api/tests/conftest.py` 如需清理事件总线
- Create: `apps/api/tests/unit/test_organization_events.py`
- Create: `development-logs/in-progress/P4-10-membership-events.md`

最低测试：

- 创建组织发布 `OrganizationCreated` 一次。
- add member 发布 `OrganizationMemberJoined` 一次。
- leave 发布 `OrganizationMemberLeft` 一次。
- role change 发布 `OrganizationMemberRoleChanged` 一次。
- 事件不包含 email/student_no/password/token。
- handler 异常不阻断主流程，沿用 P2 EventBus 语义。

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_events.py -q -p no:cacheprovider
```

## 31. P4-11：完成越权测试矩阵

目标：

- 系统性覆盖 P4 越权路径和隐私投影。

Files:

- Create: `apps/api/tests/unit/test_organization_authorization_matrix.py`
- Modify: existing P4 tests if needed
- Create: `development-logs/in-progress/P4-11-authorization-test-matrix.md`

矩阵必须覆盖：

- anonymous
- non-member
- GUEST
- MEMBER
- ADMIN
- OWNER
- SYSTEM_ADMIN
- SCHOOL_ADMIN
- ORG_ADMIN
- deleted user
- archived org
- deleted org

场景必须覆盖：

- 查看 PUBLIC/MEMBERS_ONLY/PRIVATE 组织。
- 查看成员列表。
- 添加成员。
- 修改角色。
- 移除成员。
- 删除组织。
- 加入组织。
- 退出组织。
- 目录搜索。
- 组织树。
- 用户组织列表。

任务完成后运行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_authorization_matrix.py -q -p no:cacheprovider
```

## 32. P4-12：完成组织与联系人页面

目标：

- 增加基础组织和目录前端页面。
- 不做完整 P10 App Shell。

Files:

- Create: `apps/web/src/app/organizations/page.tsx`
- Create: `apps/web/src/app/organizations/[organizationId]/page.tsx`
- Create: `apps/web/src/app/directory/page.tsx`
- Create: `apps/web/src/lib/organizations.ts`
- Create: `apps/web/src/lib/directory.ts`
- Create: `development-logs/in-progress/P4-12-organization-frontend.md`

最低要求：

- 页面可以 build。
- API helper 使用 `credentials: "include"`。
- 写请求使用 CSRF。
- 不保存 token。
- 显示 loading/error/empty。
- 显示权限错误。
- 不展示无权操作入口。

任务完成后运行：

```bash
corepack pnpm --filter @campus-agent/web lint
corepack pnpm --filter @campus-agent/web typecheck
corepack pnpm --filter @campus-agent/web test -- --runInBand
corepack pnpm --filter @campus-agent/web build
```

## 33. 文档收口

必须新增：

```text
docs/development/P4-COMPLETION-REPORT.md
```

必须更新：

```text
docs/development/DEVELOPMENT_PLAN.md
```

更新要求：

- P4-01～P4-12 标记 `[x]`。
- P4 阶段状态写为“完成，待 Codex 审计”。
- P5 仍为未开始。
- 记录新增测试数量、验证结果、未执行项。
- 不把 P4 写成已提交/已推送。

每个 P4 开发日志必须包含：

- front matter：task_id、task_name、status、started_at、completed_at、actual_hours、owner、auditor
- 背景
- 修改文件列表
- 设计说明
- 测试覆盖
- 自检命令和结果
- 未执行项
- 边界声明

## 34. 全量验证

P4 全部完成后必须执行：

```bash
cd /root/CampusAgent

git status --short --branch
git diff HEAD --check

conda run -n CampusAgent python -m pip install -r apps/api/requirements.lock
conda run -n CampusAgent pip check

conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider

corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
```

如果本地有 gitleaks：

```bash
/tmp/gitleaks detect --source . --config .gitleaks.toml --gitleaks-ignore-path .gitleaksignore --redact --verbose --no-banner
```

如果没有 gitleaks：

- 在完成报告中写：`gitleaks 本地不可用，远端 CI 会执行`。

如果 Docker 不可用：

```bash
docker --version
```

若输出 `command not found`：

- 在完成报告中写：`Docker 本地不可用，未执行 docker compose 实跑`。
- 不要因为 Docker 不可用而跳过 Python/Node 验证。

## 35. 完成报告格式

最终回复必须包含：

1. 基准信息
   - 项目路径
   - 分支
   - 起始提交
   - 是否保留 P3
2. 完成任务列表 P4-01～P4-12
3. 修改文件列表
4. 数据模型说明
5. Alembic 迁移说明
6. API 端点说明
7. 权限策略说明
8. 加入策略说明
9. 最后 OWNER 保护说明
10. 目录搜索说明
11. 组织树说明
12. 推荐占位规则说明
13. 领域事件说明
14. 前端页面说明
15. 新增/修改测试列表
16. 自检命令和结果
17. 未执行项和原因
18. 边界声明
19. `git status --short --branch` 输出

## 36. 禁止事项

严禁：

- 提交。
- 推送。
- 执行 P5+。
- 修改冻结 API/WebSocket 契约语义。
- 删除 P3 测试来让 P4 通过。
- 通过前端隐藏按钮替代后端权限。
- 在目录搜索结果中返回 email、student_no、password_hash、token、session。
- 在日志、事件、metrics label 中记录 P3/P4 敏感正文。
- 把真实学校系统账号、Kuboard 地址、密码、飞书一次性 token 写入仓库。
- 使用 localStorage/sessionStorage 保存 token。
- 引入真实模型 API。

## 37. Codex 审计重点预告

Codex 后续会重点审计：

- 最后 OWNER 是否真的无法退出/降级/被移除。
- ADMIN 是否无法操作 OWNER。
- ORG_ADMIN 是否被误当成所有组织管理员。
- PRIVATE/MEMBERS_ONLY 是否通过 search/tree/users-organizations 泄露。
- 用户字段投影是否泄露 email/student_no/password_hash。
- 写端点是否全部要求 CSRF。
- 事件是否使用 P2 `default_event_bus`，而不是新建不兼容事件总线。
- 迁移是否能 upgrade/downgrade。
- 前端是否把 token 放入 localStorage 或 URL。
- `requirements.lock` 是否被错误缩减。
- gitleaks 是否有测试假阳性。

完成后不要提交、不要推送。输出 P4 完成报告，等待 Codex 审计。
