# 变更冻结例外审批 API

本地可运行的变更冻结例外审批系统，基于 Flask + SQLite 实现。

## 目录结构

```
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
```

## 本地启动方式

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python run.py
```

服务将在 `http://127.0.0.1:5000` 启动，首次启动会自动初始化数据库并创建示例数据。

### 3. 初始化数据

启动时自动创建以下数据：

**角色:**
- `APPLICANT` (申请人): zhangsan, lisi
- `REVIEWER` (风险复核人): wangwu, zhaoliu
- `APPROVER` (审批人): qianqi, sunba

**系统:**
- `PAYMENT-SYSTEM` (核心支付系统)
- `USER-SERVICE` (用户中心服务)
- `ORDER-SYSTEM` (订单系统)
- `INVENTORY-SYSTEM` (库存系统)

## 状态图

```
                       ┌─────────────────┐
                       │ PENDING_REVIEW  │  待复核（初始状态）
                       └────────┬────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│    REVIEWED     │   │ REVIEW_REJECTED │   │   WITHDRAWN     │
│   （复核通过）  │   │  （复核拒绝）   │   │   （已撤回）    │
└────────┬────────┘   └─────────────────┘   └────────┬────────┘
          │                                            ▲
          ▼                                            │
┌─────────────────┐                                    │
│    APPROVED     │◄───────────────────────────────────┘
│   （已批准）    │        撤回后再次批准 (APPROVER)
└────────┬────────┘
          │
          ▼
┌─────────────────┐
│   EFFECTIVE     │  （已生效）
└─────────────────┘
```

### 状态转换规则

| 当前状态         | 允许转换到                    | 操作角色     |
|------------------|-----------------------------|------------|
| PENDING_REVIEW   | REVIEWED, REVIEW_REJECTED, WITHDRAWN | REVIEWER(复核)/APPLICANT(撤回) |
| REVIEWED         | APPROVED, REVIEW_REJECTED, WITHDRAWN | APPROVER(审批)/APPLICANT(撤回) |
| REVIEW_REJECTED  | WITHDRAWN                   | APPLICANT  |
| APPROVED         | EFFECTIVE, WITHDRAWN        | APPROVER(生效)/APPLICANT(撤回) |
| EFFECTIVE        | -                           | -          |
| WITHDRAWN        | APPROVED                    | APPROVER   |

## API 接口

所有接口前缀: `/api`

### 基础查询

#### 获取角色列表
```bash
curl http://127.0.0.1:5000/api/roles
```

#### 获取系统列表
```bash
curl http://127.0.0.1:5000/api/systems
```

#### 获取用户列表
```bash
curl http://127.0.0.1:5000/api/users
```

#### 获取所有申请
```bash
curl "http://127.0.0.1:5000/api/requests?username=zhangsan"
```

#### 获取单个申请详情
```bash
curl "http://127.0.0.1:5000/api/requests/1?username=zhangsan"
```

### 主流程

#### 1. 申请人提交申请
```bash
curl -X POST http://127.0.0.1:5000/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "username": "zhangsan",
    "system_id": "PAYMENT-SYSTEM",
    "window_start": "2026-06-10T00:00:00Z",
    "window_end": "2026-06-15T23:59:59Z",
    "risk_level": "MEDIUM",
    "reason": "紧急修复支付网关漏洞，需要在冻结期间上线"
  }'
```

**返回示例 (成功):**
```json
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
```

#### 2. 风险复核人复核
```bash
# 复核通过
curl -X POST http://127.0.0.1:5000/api/requests/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "username": "wangwu",
    "approved": true,
    "comment": "风险可控，已有回滚方案，同意"
  }'

# 复核拒绝
curl -X POST http://127.0.0.1:5000/api/requests/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "username": "wangwu",
    "approved": false,
    "comment": "风险过高，建议延后到冻结期后"
  }'
```

#### 3. 审批人批准
```bash
curl -X POST http://127.0.0.1:5000/api/requests/1/approve \
  -H "Content-Type: application/json" \
  -d '{
    "username": "qianqi",
    "comment": "同意，安排在凌晨低峰期执行"
  }'
```

#### 4. 审批人生效
```bash
curl -X POST http://127.0.0.1:5000/api/requests/1/effective \
  -H "Content-Type: application/json" \
  -d '{
    "username": "qianqi",
    "comment": "变更已执行并验证通过"
  }'
```

#### 5. 申请人撤回
```bash
curl -X POST http://127.0.0.1:5000/api/requests/1/withdraw \
  -H "Content-Type: application/json" \
  -d '{
    "username": "zhangsan",
    "comment": "问题已通过其他方式解决，撤回申请"
  }'
```

#### 6. 撤回后再次批准
```bash
curl -X POST http://127.0.0.1:5000/api/requests/1/re-effective \
  -H "Content-Type: application/json" \
  -d '{
    "username": "qianqi",
    "comment": "重新评估后同意再次批准"
  }'
```

### 审计记录

#### 查询全部审计日志
```bash
curl "http://127.0.0.1:5000/api/audit?username=zhangsan"
```

#### 查询单个申请的状态历史
```bash
curl "http://127.0.0.1:5000/api/requests/1/history?username=zhangsan"
```

**返回示例:**
```json
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
```

## 失败路径测试

### 1. 非法角色操作
```bash
# 申请人尝试审批
curl -X POST http://127.0.0.1:5000/api/requests/1/approve \
  -H "Content-Type: application/json" \
  -d '{"username": "zhangsan"}'
```
**返回错误:**
```json
{
  "success": false,
  "error": {
    "code": "ROLE_PERMISSION_DENIED",
    "message": "角色 \"申请人\" 无权执行此操作。允许的角色: 审批人"
  }
}
```

### 2. 未复核就审批
```bash
# 申请状态为 PENDING_REVIEW 时直接审批
curl -X POST http://127.0.0.1:5000/api/requests/1/approve \
  -H "Content-Type: application/json" \
  -d '{"username": "qianqi"}'
```
**返回错误:**
```json
{
  "success": false,
  "error": {
    "code": "NOT_REVIEWED",
    "message": "申请尚未经过风险复核，审批人无法批准。请先由复核人进行风险复核"
  }
}
```

### 3. 窗口期重叠
```bash
# 先创建一个已批准的申请
# 再创建另一个窗口期重叠的申请
curl -X POST http://127.0.0.1:5000/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "username": "lisi",
    "system_id": "PAYMENT-SYSTEM",
    "window_start": "2026-06-12T00:00:00Z",
    "window_end": "2026-06-20T23:59:59Z",
    "risk_level": "HIGH",
    "reason": "另一个变更申请"
  }'
```
**返回错误:**
```json
{
  "success": false,
  "error": {
    "code": "WINDOW_CONFLICT",
    "message": "该系统在申请的窗口期内已有已批准或已生效的变更冻结例外，窗口重叠"
  }
}
```

### 4. 撤回后再次生效（非已撤回状态）
```bash
# 申请状态为 APPROVED 时尝试再次生效
curl -X POST http://127.0.0.1:5000/api/requests/1/re-effective \
  -H "Content-Type: application/json" \
  -d '{"username": "qianqi"}'
```
**返回错误:**
```json
{
  "success": false,
  "error": {
    "code": "NOT_WITHDRAWN",
    "message": "只有已撤回的申请才能再次生效"
  }
}
```

## 数据持久化

所有数据保存在 SQLite 数据库文件 `change_freeze.db` 中：
- `roles`: 角色表
- `systems`: 系统表
- `users`: 用户表（关联角色）
- `change_requests`: 变更申请表
- `status_history`: 状态历史表（审计日志）

重启服务后，所有申请状态、状态历史和冲突判断都将保持一致。

## 错误码说明

| 错误码 | 说明 |
|-------|------|
| `INVALID_STATUS` | 无效的状态值 |
| `INVALID_TRANSITION` | 不允许的状态转换 |
| `INVALID_RISK_LEVEL` | 无效的风险等级 |
| `INVALID_DATETIME_FORMAT` | 日期时间格式错误 |
| `INVALID_WINDOW_RANGE` | 窗口期时间范围无效 |
| `WINDOW_CONFLICT` | 窗口期与已批准/已生效申请重叠 |
| `NOT_REVIEWED` | 未经过风险复核 |
| `REVIEW_REJECTED` | 已被复核拒绝 |
| `ALREADY_EFFECTIVE` | 已生效，无法撤回 |
| `NOT_WITHDRAWN` | 非已撤回状态，无法再次生效 |
| `USER_NOT_FOUND` | 用户不存在 |
| `ROLE_PERMISSION_DENIED` | 角色无权限 |
| `NOT_APPLICANT` | 非申请人本人 |
| `APPLICANT_CANNOT_REVIEW` | 申请人不能复核自己的申请 |
| `APPLICANT_CANNOT_APPROVE` | 申请人不能批准自己的申请 |
| `SYSTEM_NOT_FOUND` | 系统不存在 |
| `REQUEST_NOT_FOUND` | 申请不存在 |
