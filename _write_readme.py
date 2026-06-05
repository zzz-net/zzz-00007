# -*- coding: utf-8 -*-
content = """# 变更冻结例外审批 API

本地可运行的变更冻结例外审批系统，基于 Flask + SQLite 实现。

## 目录结构

\`\`\`
├── app/
│   ├── __init__.py          # Flask 应用工厂
│   ├── models.py            # 数据模型 (SQLAlchemy)
│   ├── storage.py           # 存储层 (CRUD)
│   ├── state_validator.py   # 状态校验层 (状态机、冲突检测)
│   ├── permissions.py       # 权限判断层 (角色权限)
│   └── routes.py            # 路由层 (API 端点)
├── init_db.py               # 数据库初始化脚本
├── run.py                   # 主入口
├── requirements.txt         # 依赖
└── README.md                # 本文档
\`\`\`

## 本地启动方式

### 1. 安装依赖

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 2. 启动服务

\`\`\`bash
python run.py
\`\`\`

服务将在 \`http://127.0.0.1:5000\` 启动，首次启动会自动初始化数据库并创建示例数据。

### 3. 初始化数据

启动时自动创建以下数据：

**角色:**
- \`APPLICANT\` (申请人): zhangsan, lisi
- \`REVIEWER\` (风险复核人): wangwu, zhaoliu
- \`APPROVER\` (审批人): qianqi, sunba

**系统:**
- \`PAYMENT-SYSTEM\` (核心支付系统)
- \`USER-SERVICE\` (用户中心服务)
- \`ORDER-SYSTEM\` (订单系统)
- \`INVENTORY-SYSTEM\` (库存系统)

## 状态图

\`\`\`
                       ┌─────────────────┐
                       │ PENDING_REVIEW  │  待复核（初始状态）
                       └────────┬────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│    REVIEWED     │   │ REVIEW_REJECTED │   │   WITHDRAWN     │
│   （复核通过）  │   │  （复核拒绝）   │   │   （已撤回）    │
└────────┬────────┘   └─────────────────┘   └─────────────────┘
          │                                    （终态，不可再变更）
          ▼
┌─────────────────┐
│    APPROVED     │
│   （已批准）    │
└────────┬────────┘
          │
          ▼
┌─────────────────┐
│   EFFECTIVE     │  （已生效）
└─────────────────┘
\`\`\`

### 状态转换规则

| 当前状态         | 允许转换到                    | 操作角色     |
|------------------|-----------------------------|------------|
| PENDING_REVIEW   | REVIEWED, REVIEW_REJECTED, WITHDRAWN | REVIEWER(复核)/APPLICANT(撤回) |
| REVIEWED         | APPROVED, REVIEW_REJECTED, WITHDRAWN | APPROVER(审批)/APPLICANT(撤回) |
| REVIEW_REJECTED  | WITHDRAWN                   | APPLICANT  |
| APPROVED         | EFFECTIVE, WITHDRAWN        | APPROVER(生效)/APPLICANT(撤回) |
| EFFECTIVE        | WITHDRAWN                   | APPLICANT  |
| WITHDRAWN        | -                           | -          |

## API 接口

所有接口前缀: \`/api\`

### 基础查询

#### 获取角色列表
\`\`\`bash
curl http://127.0.0.1:5000/api/roles
\`\`\`

#### 获取系统列表
\`\`\`bash
curl http://127.0.0.1:5000/api/systems
\`\`\`

#### 获取用户列表
\`\`\`bash
curl http://127.0.0.1:5000/api/users
\`\`\`

#### 获取所有申请
\`\`\`bash
curl "http://127.0.0.1:5000/api/requests?username=zhangsan"
\`\`\`

#### 获取单个申请详情
\`\`\`bash
curl "http://127.0.0.1:5000/api/requests/1?username=zhangsan"
\`\`\`

### 主流程

#### 1. 申请人提交申请
\`\`\`bash
curl -X POST http://127.0.0.1:5000/api/requests \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "zhangsan",
    "system_id": "PAYMENT-SYSTEM",
    "window_start": "2026-06-10T00:00:00Z",
    "window_end": "2026-06-15T23:59:59Z",
    "risk_level": "MEDIUM",
    "reason": "紧急修复支付网关漏洞，需要在冻结期间上线"
  }'
\`\`\`

**返回示例 (成功):**
\`\`\`json
{
  "success": true,
  "message": "申请提交成功",
  "data": {
    "id": 1,
    "status": "PENDING_REVIEW",
    "risk_level": "MEDIUM",
    "window_start": "2026-06-10T00:00:00Z",
    "window_end": "2026-06-15T23:59:59Z"
  }
}
\`\`\`

#### 2. 风险复核人复核
\`\`\`bash
# 复核通过
curl -X POST http://127.0.0.1:5000/api/requests/1/review \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "wangwu",
    "approved": true,
    "comment": "风险可控，已有回滚方案，同意"
  }'

# 复核拒绝
curl -X POST http://127.0.0.1:5000/api/requests/1/review \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "wangwu",
    "approved": false,
    "comment": "风险过高，建议延后到冻结期后"
  }'
\`\`\`

#### 3. 审批人批准
\`\`\`bash
curl -X POST http://127.0.0.1:5000/api/requests/1/approve \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "qianqi",
    "comment": "同意，安排在凌晨低峰期执行"
  }'
\`\`\`

#### 4. 审批人生效
\`\`\`bash
curl -X POST http://127.0.0.1:5000/api/requests/1/effective \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "qianqi",
    "comment": "变更已执行并验证通过"
  }'
\`\`\`

#### 5. 申请人撤回
\`\`\`bash
curl -X POST http://127.0.0.1:5000/api/requests/1/withdraw \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "zhangsan",
    "comment": "问题已通过其他方式解决，撤回申请"
  }'
\`\`\`

> **重要**: 撤回是终态操作。申请一旦撤回，状态保持为 WITHDRAWN，无法再次批准、生效或通过任何接口修改，审计历史也不会新增记录。如需重新申请，请创建新的变更申请。

### 审计记录

#### 查询全部审计日志
\`\`\`bash
curl "http://127.0.0.1:5000/api/audit?username=zhangsan"
\`\`\`


#### 按申请ID过滤审计日志

**接口格式:** \`/api/audit?username=...&request_id=...\`

\`\`\`bash
# 只返回指定申请的审计记录
curl "http://127.0.0.1:5000/api/audit?username=zhangsan&request_id=1"
\`\`\`

**参数说明:**
- \`username\`: 必需，用于权限验证
- \`request_id\`: 可选，整数，用于过滤指定申请的审计记录
  - 不传或传空值：返回全量审计记录
  - 传非整数：返回 400 错误 \`INVALID_REQUEST_ID\`
  - 传不存在的申请ID：返回 404 错误 \`REQUEST_NOT_FOUND\`

#### 查询单个申请的状态历史
\`\`\`bash
curl "http://127.0.0.1:5000/api/requests/1/history?username=zhangsan"
\`\`\`

**返回示例:**
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "request_id": 1,
      "from_status": null,
      "to_status": "PENDING_REVIEW",
      "operator": {"username": "zhangsan", "role": "APPLICANT"},
      "comment": "提交申请",
      "created_at": "2026-06-05T10:30:00Z"
    },
    {
      "id": 2,
      "request_id": 1,
      "from_status": "PENDING_REVIEW",
      "to_status": "REVIEWED",
      "operator": {"username": "wangwu", "role": "REVIEWER"},
      "comment": "风险可控",
      "created_at": "2026-06-05T11:00:00Z"
    }
  ]
}
\`\`\`

## 导入导出

### CSV 字段说明

导入导出使用 UTF-8 编码的 CSV 文件，包含以下字段：

| 字段名     | 必填 | 说明                                                                 |
|------------|------|----------------------------------------------------------------------|
| 标题       | 是   | 变更申请的标题，最长 200 字符                                        |
| 系统       | 是   | 系统名称，必须是已存在的系统（如 \`PAYMENT-SYSTEM\`, \`USER-SERVICE\` 等）|
| 窗口开始   | 是   | 窗口期开始时间，格式：\`YYYY-MM-DDTHH:MM:SSZ\`（UTC 时间）             |
| 窗口结束   | 是   | 窗口期结束时间，格式：\`YYYY-MM-DDTHH:MM:SSZ\`（UTC 时间），必须晚于开始时间 |
| 风险等级   | 是   | 风险等级，可选值：\`LOW\`, \`MEDIUM\`, \`HIGH\`                            |
| 风险说明   | 是   | 变更的原因和风险说明，最长 1000 字符                                  |
| 备注       | 否   | 额外备注信息，最长 500 字符                                          |

### CSV 示例（可直接保存使用）

将以下内容保存为 \`import_example.csv\`（注意使用 UTF-8 编码）：

\`\`\`csv
标题,系统,窗口开始,窗口结束,风险等级,风险说明,备注
支付网关安全升级,PAYMENT-SYSTEM,2026-06-20T00:00:00Z,2026-06-25T23:59:59Z,HIGH,紧急修复支付网关安全漏洞,需凌晨执行
用户中心性能优化,USER-SERVICE,2026-07-01T00:00:00Z,2026-07-05T23:59:59Z,MEDIUM,优化用户查询接口性能,
订单系统Bug修复,ORDER-SYSTEM,2026-07-10T00:00:00Z,2026-07-15T23:59:59Z,LOW,修复订单状态同步问题,低风险变更
\`\`\`

### 导出申请

**权限要求**: \`APPLICANT\`, \`REVIEWER\`, \`APPROVER\`
- 申请人只能导出自己的申请
- 复核人、审批人可以导出所有申请

\`\`\`bash
# 导出所有可见申请（CSV 格式）
curl -o change_requests.csv "http://127.0.0.1:5000/api/requests/export?username=zhangsan"
\`\`\`

**成功响应** (HTTP 200):
\`\`\`
Content-Type: text/csv; charset=utf-8-sig
Content-Disposition: attachment; filename=change_requests_20260605_120000.csv

标题,系统,窗口开始,窗口结束,风险等级,风险说明,备注
支付网关安全升级,PAYMENT-SYSTEM,2026-06-20T00:00:00Z,2026-06-25T23:59:59Z,HIGH,紧急修复支付网关安全漏洞,需凌晨执行
...
\`\`\`

**权限拒绝响应** (HTTP 403):
\`\`\`json
{
  "success": false,
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "用户不存在: invalid_user"
  }
}
\`\`\`

### 批量导入申请

**权限要求**: \`APPLICANT\`（仅申请人可导入）

\`\`\`bash
# 从 CSV 文件批量导入申请
curl -X POST http://127.0.0.1:5000/api/requests/import \\
  -F "username=zhangsan" \\
  -F "file=@import_example.csv;type=text/csv"
\`\`\`

**全部成功响应** (HTTP 200):
\`\`\`json
{
  "success": true,
  "message": "导入完成：成功 3 条，失败 0 条",
  "data": {
    "batch_no": "IMP_20260605120000_a1b2c3d4",
    "total_count": 3,
    "success_count": 3,
    "fail_count": 0,
    "success_ids": [101, 102, 103],
    "failed_rows": []
  }
}
\`\`\`

**部分失败响应** (HTTP 200):
\`\`\`json
{
  "success": true,
  "message": "导入完成：成功 2 条，失败 1 条",
  "data": {
    "batch_no": "IMP_20260605120000_a1b2c3d4",
    "total_count": 3,
    "success_count": 2,
    "fail_count": 1,
    "success_ids": [101, 103],
    "failed_rows": [
      {
        "row": 3,
        "code": "SYSTEM_NOT_FOUND",
        "message": "系统不存在: INVALID-SYSTEM"
      }
    ]
  }
}
\`\`\`

**权限拒绝响应** (HTTP 403):
\`\`\`json
{
  "success": false,
  "error": {
    "code": "ROLE_PERMISSION_DENIED",
    "message": "角色 \"风险复核人\" 无权执行此操作。允许的角色: 申请人"
  }
}
\`\`\`

**CSV 格式错误响应** (HTTP 400):
\`\`\`json
{
  "success": false,
  "error": {
    "code": "MISSING_COLUMN",
    "message": "缺少必填列: 风险等级"
  }
}
\`\`\`

### 查询导入批次列表

**权限要求**: \`APPLICANT\`, \`REVIEWER\`, \`APPROVER\`

\`\`\`bash
curl "http://127.0.0.1:5000/api/import/batches?username=zhangsan"
\`\`\`

**成功响应** (HTTP 200):
\`\`\`json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "batch_no": "IMP_20260605120000_a1b2c3d4",
      "operator": {
        "id": 1,
        "username": "zhangsan",
        "role": "APPLICANT"
      },
      "total_count": 3,
      "success_count": 2,
      "fail_count": 1,
      "created_at": "2026-06-05T12:00:00Z"
    }
  ]
}
\`\`\`

### 查询批次详情（明细）

**权限要求**: \`APPLICANT\`, \`REVIEWER\`, \`APPROVER\`

\`\`\`bash
# 使用批次号查询明细
curl "http://127.0.0.1:5000/api/import/batches/IMP_20260605120000_a1b2c3d4/records?username=zhangsan"
\`\`\`

**成功响应** (HTTP 200):
\`\`\`json
{
  "success": true,
  "data": {
    "batch": {
      "id": 1,
      "batch_no": "IMP_20260605120000_a1b2c3d4",
      "operator": {
        "id": 1,
        "username": "zhangsan",
        "role": "APPLICANT"
      },
      "total_count": 3,
      "success_count": 2,
      "fail_count": 1,
      "created_at": "2026-06-05T12:00:00Z"
    },
    "records": [
      {
        "row_no": 2,
        "success": true,
        "error_code": null,
        "error_message": null,
        "request_id": 101
      },
      {
        "row_no": 3,
        "success": false,
        "error_code": "SYSTEM_NOT_FOUND",
        "error_message": "系统不存在: INVALID-SYSTEM",
        "request_id": null
      },
      {
        "row_no": 4,
        "success": true,
        "error_code": null,
        "error_message": null,
        "request_id": 103
      }
    ]
  }
}
\`\`\`

**批次不存在响应** (HTTP 404):
\`\`\`json
{
  "success": false,
  "error": {
    "code": "BATCH_NOT_FOUND",
    "message": "批次不存在: IMP_INVALID"
  }
}
\`\`\`

### 窗口冲突场景说明

导入时，如果某行数据的窗口期与同一系统已批准/已生效的申请窗口重叠，该行会失败（返回 \`WINDOW_CONFLICT\` 错误），但其他合法行仍会成功落库。

**示例响应**（第 3 行冲突）:
\`\`\`json
{
  "success": true,
  "message": "导入完成：成功 2 条，失败 1 条",
  "data": {
    "batch_no": "IMP_20260605120000_e5f6g7h8",
    "total_count": 3,
    "success_count": 2,
    "fail_count": 1,
    "success_ids": [104, 106],
    "failed_rows": [
      {
        "row": 3,
        "code": "WINDOW_CONFLICT",
        "message": "该系统在申请的窗口期内已有已批准或已生效的变更冻结例外，窗口重叠"
      }
    ]
  }
}
\`\`\`

## 失败路径测试

### 1. 非法角色操作
\`\`\`bash
# 申请人尝试审批
curl -X POST http://127.0.0.1:5000/api/requests/1/approve \\
  -H "Content-Type: application/json" \\
  -d '{"username": "zhangsan"}'
\`\`\`
**返回错误:**
\`\`\`json
{
  "success": false,
  "error": {
    "code": "ROLE_PERMISSION_DENIED",
    "message": "角色 \"申请人\" 无权执行此操作。允许的角色: 审批人"
  }
}
\`\`\`

### 2. 未复核就审批
\`\`\`bash
# 申请状态为 PENDING_REVIEW 时直接审批
curl -X POST http://127.0.0.1:5000/api/requests/1/approve \\
  -H "Content-Type: application/json" \\
  -d '{"username": "qianqi"}'
\`\`\`
**返回错误:**
\`\`\`json
{
  "success": false,
  "error": {
    "code": "NOT_REVIEWED",
    "message": "申请尚未经过风险复核，审批人无法批准。请先由复核人进行风险复核"
  }
}
\`\`\`

### 3. 窗口期重叠
\`\`\`bash
# 先创建一个已批准的申请
# 再创建另一个窗口期重叠的申请
curl -X POST http://127.0.0.1:5000/api/requests \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "lisi",
    "system_id": "PAYMENT-SYSTEM",
    "window_start": "2026-06-12T00:00:00Z",
    "window_end": "2026-06-20T23:59:59Z",
    "risk_level": "HIGH",
    "reason": "另一个变更申请"
  }'
\`\`\`
**返回错误:**
\`\`\`json
{
  "success": false,
  "error": {
    "code": "WINDOW_CONFLICT",
    "message": "该系统在申请的窗口期内已有已批准或已生效的变更冻结例外，窗口重叠"
  }
}
\`\`\`

### 4. 撤回后尝试再次批准
\`\`\`bash
# 申请状态为 WITHDRAWN 时尝试再次批准
curl -X POST http://127.0.0.1:5000/api/requests/1/re-effective \\
  -H "Content-Type: application/json" \\
  -d '{"username": "qianqi"}'
\`\`\`
**返回错误:**
\`\`\`json
{
  "success": false,
  "error": {
    "code": "WITHDRAWN_FINAL_STATE",
    "message": "申请已撤回，是终态，无法再次批准或生效。如需重新申请，请创建新的变更申请"
  }
}
\`\`\`

### 5. 审计查询使用无效的 request_id
\`\`\`bash
# 使用非整数的 request_id
curl "http://127.0.0.1:5000/api/audit?username=zhangsan&request_id=abc"
\`\`\`
**返回错误:**
\`\`\`json
{
  "success": false,
  "error": {
    "code": "INVALID_REQUEST_ID",
    "message": "request_id 参数无效，必须是整数: abc"
  }
}
\`\`\`

### 6. 审计查询使用不存在的 request_id
\`\`\`bash
# 使用不存在的 request_id
curl "http://127.0.0.1:5000/api/audit?username=zhangsan&request_id=99999"
\`\`\`
**返回错误:**
\`\`\`json
{
  "success": false,
  "error": {
    "code": "REQUEST_NOT_FOUND",
    "message": "申请不存在: 99999"
  }
}
\`\`\`

## 数据持久化

所有数据保存在 SQLite 数据库文件 \`instance/change_freeze.db\` 中（与 Flask 配置一致，位于项目根目录下的 \`instance\` 文件夹）：

- \`roles\`: 角色表
- \`systems\`: 系统表
- \`users\`: 用户表（关联角色）
- \`change_requests\`: 变更申请表
- \`import_batches\`: 导入批次表
- \`import_records\`: 导入明细表（每行导入结果）
- \`status_history\`: 状态历史表（审计日志）

重启服务后，所有申请状态、导入批次、状态历史和冲突判断都将保持一致。

## 错误码说明

| 错误码 | 说明 |
|-------|------|
| \`INVALID_STATUS\` | 无效的状态值 |
| \`INVALID_TRANSITION\` | 不允许的状态转换 |
| \`INVALID_RISK_LEVEL\` | 无效的风险等级 |
| \`INVALID_DATETIME_FORMAT\` | 日期时间格式错误 |
| \`INVALID_WINDOW_RANGE\` | 窗口期时间范围无效 |
| \`WINDOW_CONFLICT\` | 窗口期与已批准/已生效申请重叠 |
| \`NOT_REVIEWED\` | 未经过风险复核 |
| \`REVIEW_REJECTED\` | 已被复核拒绝 |
| \`ALREADY_EFFECTIVE\` | 已生效，无法撤回 |
| \`WITHDRAWN_FINAL_STATE\` | 申请已撤回，是终态，无法再次批准或生效。状态保持 WITHDRAWN，审计历史不新增记录 |
| \`INVALID_REQUEST_ID\` | request_id 参数无效，必须是整数 |
| \`USER_NOT_FOUND\` | 用户不存在 |
| \`ROLE_PERMISSION_DENIED\` | 角色无权限 |
| \`NOT_APPLICANT\` | 非申请人本人 |
| \`APPLICANT_CANNOT_REVIEW\` | 申请人不能复核自己的申请 |
| \`APPLICANT_CANNOT_APPROVE\` | 申请人不能批准自己的申请 |
| \`SYSTEM_NOT_FOUND\` | 系统不存在 |
| \`REQUEST_NOT_FOUND\` | 申请不存在 |
| \`MISSING_FILE\` | 缺少上传文件 |
| \`EMPTY_FILENAME\` | 文件名为空 |
| \`INVALID_FILE_FORMAT\` | 文件格式无效，只支持 CSV |
| \`MISSING_COLUMN\` | CSV 缺少必填列 |
| \`EMPTY_FILE\` | CSV 文件为空 |
| \`MISSING_TITLE\` | 标题不能为空 |
| \`MISSING_SYSTEM\` | 系统不能为空 |
| \`MISSING_WINDOW_START\` | 窗口开始不能为空 |
| \`MISSING_WINDOW_END\` | 窗口结束不能为空 |
| \`MISSING_RISK_LEVEL\` | 风险等级不能为空 |
| \`MISSING_REASON\` | 风险说明不能为空 |
| \`BATCH_NOT_FOUND\` | 导入批次不存在 |
"""

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)

print('README written successfully!')
print('Size:', len(content))

with open('README.md', 'rb') as f:
    check = f.read().decode('utf-8')
print('Has instance/change_freeze.db:', 'instance/change_freeze.db' in check)
print('Has 导入导出:', '导入导出' in check)
print('Has CSV 字段说明:', 'CSV 字段说明' in check)
