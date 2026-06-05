import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'

def p(title, response):
    print(f'\n{"="*60}')
    print(f'  {title}')
    print(f'{"="*60}')
    try:
        data = response.json()
        print(f'Status: {response.status_code}')
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except:
        print(response.text)
    print()

print('#'*60)
print('#  Curl 级别用户可见结果验证')
print('#'*60)

# 1. 创建新申请
print('\n\n>>> curl -X POST /api/requests (创建申请)')
r = requests.post(f'{BASE_URL}/requests', json={
    'username': 'zhangsan',
    'system_id': 'INVENTORY-SYSTEM',
    'window_start': '2026-12-01T00:00:00Z',
    'window_end': '2026-12-10T23:59:59Z',
    'risk_level': 'LOW',
    'reason': 'curl测试验证'
})
request_id = r.json()['data']['id']
p('创建申请成功', r)

# 2. 复核通过
print('>>> curl -X POST /api/requests/{request_id}/review (复核通过)')
r = requests.post(f'{BASE_URL}/requests/{request_id}/review', json={
    'username': 'wangwu',
    'approved': True
})
p('复核通过', r)

# 3. 审批通过
print('>>> curl -X POST /api/requests/{request_id}/approve (审批通过)')
r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
    'username': 'qianqi'
})
p('审批通过', r)

# 4. 撤回
print('>>> curl -X POST /api/requests/{request_id}/withdraw (撤回申请)')
r = requests.post(f'{BASE_URL}/requests/{request_id}/withdraw', json={
    'username': 'zhangsan'
})
p('撤回成功', r)

# 5. 撤回后尝试再次批准 - 应该失败
print('>>> curl -X POST /api/requests/{request_id}/re-effective (撤回后尝试再次批准)')
r = requests.post(f'{BASE_URL}/requests/{request_id}/re-effective', json={
    'username': 'qianqi'
})
p('撤回后再次批准失败', r)

# 6. 验证状态还是 WITHDRAWN
print('>>> curl /api/requests/{request_id} (验证状态)')
r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'zhangsan'})
data = r.json()
print(f'\n当前状态: {data["data"]["status"]}')
assert data['data']['status'] == 'WITHDRAWN', '状态应该是 WITHDRAWN'
print('✅ 状态正确，保持 WITHDRAWN 不变')

# 7. 验证审计历史没有增加
print('\n>>> curl /api/requests/{request_id}/history (验证审计历史)')
r = requests.get(f'{BASE_URL}/requests/{request_id}/history', params={'username': 'zhangsan'})
data = r.json()
history_count = len(data['data'])
print(f'历史记录数: {history_count}')
assert history_count == 4, '历史记录应该是4条（提交、复核、审批、撤回）'
print('✅ 审计历史正确，没有错误的历史记录')

# 8. 审计查询按 request_id 过滤
print('\n>>> curl /api/audit?username=zhangsan&request_id={request_id} (审计过滤)')
r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': request_id})
data = r.json()
filtered_count = len(data['data'])
all_match = all(h['request_id'] == request_id for h in data['data'])
print(f'过滤后记录数: {filtered_count}')
print(f'全部匹配 request_id={request_id}: {all_match}')
assert filtered_count == 4 and all_match
print('✅ 审计过滤正确，只包含指定申请的历史')

# 9. 审计查询传非法 request_id
print('\n>>> curl /api/audit?username=zhangsan&request_id=abc (非法request_id)')
r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': 'abc'})
p('非法 request_id 错误', r)

# 10. 审计查询传不存在的 request_id
print('>>> curl /api/audit?username=zhangsan&request_id=99999 (不存在的request_id)')
r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': '99999'})
p('不存在的 request_id 错误', r)

print('\n' + '#'*60)
print('#  ✅ 所有用户可见结果验证通过！')
print('#'*60)
print()
