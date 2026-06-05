import requests

BASE_URL = 'http://127.0.0.1:5000/api'

print('=' * 70)
print('用户可见结果验证：Python requests 复现')
print('=' * 70)

APPROVER = 'qianqi'  # 审批人是 qianqi

# 先找到一个已经撤回的申请，或者创建一个新的
print('\n--- 先查找一个已撤回的申请 ---')
r = requests.get(f'{BASE_URL}/requests', params={'username': 'zhangsan'})
all_requests = r.json()['data']
withdrawn_request = None
for req in all_requests:
    if req['status'] == 'WITHDRAWN':
        withdrawn_request = req
        break

if withdrawn_request:
    request_id = withdrawn_request['id']
    print(f'找到已撤回的申请ID: {request_id}')
else:
    print('未找到已撤回的申请，创建新的...')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'system_id': 1,
        'window_start': '2027-02-01T00:00:00Z',
        'window_end': '2027-02-01T23:59:59Z',
        'risk_level': 'LOW',
        'reason': '测试申请'
    })
    data = r.json()
    if not data['success']:
        print(f'创建失败: {data}')
        exit(1)
    request_id = data['data']['id']
    print(f'创建成功，申请ID: {request_id}')
    
    # 复核
    r = requests.post(f'{BASE_URL}/requests/{request_id}/review', json={
        'username': 'wangwu',
        'approved': True
    })
    print(f'复核: {r.json()["success"]}')
    
    # 撤回
    r = requests.post(f'{BASE_URL}/requests/{request_id}/withdraw', json={
        'username': 'zhangsan',
        'reason': '测试撤回'
    })
    print(f'撤回: {r.json()["success"]}')

# 检查撤回后的状态
r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'zhangsan'})
data = r.json()
status_after = data['data']['status']
print(f'撤回后状态: {status_after}')

r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': request_id})
audit_count_after = len(r.json()['data'])
print(f'审计记录数: {audit_count_after}')

print('\n' + '=' * 70)
print('验证撤回后三个接口失败')
print('=' * 70)

print('\n[验证1] 撤回后调用 re-effective...')
r = requests.post(f'{BASE_URL}/requests/{request_id}/re-effective', json={
    'username': APPROVER
})
data = r.json()
print(f'   状态码: {r.status_code}')
print(f'   成功: {data["success"]}')
error_code = data.get('error', {}).get('code')
error_msg = data.get('error', {}).get('message')
print(f'   错误码: {error_code}')
print(f'   错误信息: {error_msg}')
assert data['success'] == False
assert error_code == 'WITHDRAWN_FINAL_STATE'
print('   ✅ 正确返回 WITHDRAWN_FINAL_STATE')

r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'zhangsan'})
print(f'   状态不变: {r.json()["data"]["status"]}')
r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': request_id})
print(f'   审计不变: {len(r.json()["data"])}')

print('\n[验证2] 撤回后调用 approve...')
r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
    'username': APPROVER
})
data = r.json()
print(f'   状态码: {r.status_code}')
error_code = data.get('error', {}).get('code')
print(f'   错误码: {error_code}')
assert data['success'] == False
assert error_code == 'WITHDRAWN_FINAL_STATE'
print('   ✅ 正确返回 WITHDRAWN_FINAL_STATE')

print('\n[验证3] 撤回后调用 effective...')
r = requests.post(f'{BASE_URL}/requests/{request_id}/effective', json={
    'username': APPROVER
})
data = r.json()
print(f'   状态码: {r.status_code}')
error_code = data.get('error', {}).get('code')
print(f'   错误码: {error_code}')
assert data['success'] == False
assert error_code == 'WITHDRAWN_FINAL_STATE'
print('   ✅ 正确返回 WITHDRAWN_FINAL_STATE')

print('\n' + '=' * 70)
print('验证审计查询过滤')
print('=' * 70)

print('\n[验证4] 不传 request_id 返回全量...')
r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan'})
data = r.json()
print(f'   状态码: {r.status_code}, 记录数: {len(data["data"])}')
assert data['success'] == True
print('   ✅ 返回全量')

print('\n[验证5] 传 request_id 只返回该申请...')
r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': request_id})
data = r.json()
print(f'   状态码: {r.status_code}, 记录数: {len(data["data"])}')
all_match = all(h['request_id'] == request_id for h in data['data'])
print(f'   全部匹配 request_id: {all_match}')
assert all_match
print('   ✅ 过滤正确')

print('\n[验证6] 传非法 request_id (非整数)...')
r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': 'abc'})
data = r.json()
print(f'   状态码: {r.status_code}')
error_code = data.get('error', {}).get('code')
print(f'   错误码: {error_code}')
assert r.status_code == 400
assert error_code == 'INVALID_REQUEST_ID'
print('   ✅ 正确返回 INVALID_REQUEST_ID (400)')

print('\n[验证7] 传不存在的 request_id...')
r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': '99999'})
data = r.json()
print(f'   状态码: {r.status_code}')
error_code = data.get('error', {}).get('code')
print(f'   错误码: {error_code}')
assert r.status_code == 404
assert error_code == 'REQUEST_NOT_FOUND'
print('   ✅ 正确返回 REQUEST_NOT_FOUND (404)')

print('\n' + '=' * 70)
print('✅ 所有用户可见结果验证通过！')
print('=' * 70)
