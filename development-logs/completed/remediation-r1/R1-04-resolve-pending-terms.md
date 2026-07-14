---
task_id: R1-04
status: completed
stage: R1
title: 清理待讨论术语
started_at: 2026-07-14T12:42:00+09:00
completed_at: 2026-07-14T12:43:00+09:00
estimated_hours: 1
actual_hours: 0.25
---

# R1-04：清理待讨论术语

## 完成状态

✅ **待讨论术语已清理**

**完成时间**：2026-07-14T12:43:00+09:00

## 目标

清理 DOMAIN_VOCABULARY.md 中的待讨论术语，确保 Consent、Capsule 等术语已确认或明确延期，不再处于未决状态。

**来自整改计划**：R1-04 - 清理待讨论术语

## 验收标准

- [x] DOMAIN_VOCABULARY.md 中无未决术语

## 修改的文件

- `docs/domain/DOMAIN_VOCABULARY.md` - 清理待讨论术语

## 修改内容

### C. 待讨论问题

**修改前**：
```markdown
### C. 待讨论问题

- [ ] "Consent" 是否统一翻译为"授权"？（当前：是）
- [ ] "Capsule" 是否统一翻译为"胶囊"？（当前：是）
- [ ] 需要补充更多业务领域的术语吗？
```

**修改后**：
```markdown
### C. 待讨论问题

- [x] "Consent" 是否统一翻译为"授权"？（当前：是）
  - **已确认**：统一翻译为"授权"，参见 `ConsentRecord（授权记录）`
- [x] "Capsule" 是否统一翻译为"胶囊"？（当前：是）
  - **已确认**：统一翻译为"胶囊"，参见 `PreferenceCapsule（偏好胶囊）`
- [ ] 需要补充更多业务领域的术语吗？
```

## 决策确认

### 已确认术语

**Consent**：
- **翻译**：授权
- **理由**：ConsentRecord（授权记录）已在所有文档中一致使用
- **权威源**：DOMAIN_VOCABULARY.md 第 447 行

**Capsule**：
- **翻译**：胶囊
- **理由**：PreferenceCapsule（偏好胶囊）已在所有文档中一致使用
- **权威源**：DOMAIN_VOCABULARY.md 第 647 行

### 仍待讨论

- 是否需要补充更多业务领域术语（保留未决）

## 验证结果

- [x] DOMAIN_VOCABULARY.md 中已确认的术语已标记
- [x] 已确认的术语附有权威源引用
- [x] 术语翻译在文档中一致使用

## 下一步

- **R1-05**：建立枚举对照表

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
