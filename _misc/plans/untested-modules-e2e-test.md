# 未测试模块 E2E 测试计划

## 概述
为 11 个未测试的 API 模块编写 E2E 测试，分 4 个测试文件。

## 测试文件

### 1. test_e2e_project_management.py (P0)
- **projects.py** (6 endpoints): list/create/get/update/recalculate-stats/delete
- **characters.py** (5 endpoints): list/get/create/update/deactivate

### 2. test_e2e_backup_wizard.py (P1)
- **backup.py** (4 endpoints): list/create/restore/delete
- **wizard.py** (3 endpoints): generate-idea/generate-outline/confirm-outline

### 3. test_e2e_feedback_revision_compare.py (P2)
- **feedback.py** (4 endpoints): list/create/update/delete
- **revision_log.py** (3 endpoints): list/create/get
- **compare.py** (3 endpoints): diff/side-by-side/chapters

### 4. test_e2e_trash_tokens_snapshots.py (P3)
- **trash.py** (3 endpoints): list/restore/empty
- **tokens.py** (2 endpoints): count/estimate
- **snapshots.py** (4 endpoints): list/create/restore/compare
