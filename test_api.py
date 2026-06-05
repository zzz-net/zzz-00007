import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'

def print_response(title, response):
    print(f'\n{"="*60}')
    print(f'  {title}')
    print(f'{"="*60}')
    print(f'Status: {response.status_code}')
    try:
        data = response.json()
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except:
        print(response.text)
    print()

def test_main_flow():
    print('\n' + '#'*60)
    print('#  主流程测试')
    print('#'*60)

    print('\n1. 申请人提交申请')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '支付网关漏洞修复',
        'system_id': 'PAYMENT-SYSTEM',
        'window_start': '2026-06-10T00:00:00Z',
        'window_end': '2026-06-15T23:59:59Z',
        'risk_level': 'MEDIUM',
        'reason': '紧急修复支付网关漏洞'
    })
    print_response('提交申请', r)
    request_id = r.json()['data']['id']

    print('\n2. 风险复核人复核通过')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/review', json={
        'username': 'wangwu',
        'approved': True,
        'comment': '风险可控，已有回滚方案'
    })
    print_response('复核通过', r)

    print('\n3. 审批人批准')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
        'username': 'qianqi',
        'comment': '同意，安排在凌晨低峰期执行'
    })
    print_response('审批通过', r)

    print('\n4. 审批人生效')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/effective', json={
        'username': 'qianqi',
        'comment': '变更已执行并验证通过'
    })
    print_response('生效', r)

    return request_id

def test_withdraw_and_re_effective():
    print('\n' + '#'*60)
    print('#  撤回和再次生效测试')
    print('#'*60)

    print('\n1. 创建新申请')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'lisi',
        'title': '用户服务性能优化',
        'system_id': 'USER-SERVICE',
        'window_start': '2026-07-01T00:00:00Z',
        'window_end': '2026-07-05T23:59:59Z',
        'risk_level': 'LOW',
        'reason': '用户服务性能优化'
    })
    print_response('提交申请', r)
    request_id = r.json()['data']['id']

    print('\n2. 复核通过')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/review', json={
        'username': 'zhaoliu',
        'approved': True
    })
    print_response('复核通过', r)

    print('\n3. 审批通过')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
        'username': 'sunba'
    })
    print_response('审批通过', r)

    print('\n4. 申请人撤回')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/withdraw', json={
        'username': 'lisi',
        'comment': '优化方案调整，暂时撤回'
    })
    print_response('撤回申请', r)

    print('\n5. 审批人再次批准')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/re-effective', json={
        'username': 'sunba',
        'comment': '重新评估后同意'
    })
    print_response('再次批准', r)

    return request_id

def test_failure_paths():
    print('\n' + '#'*60)
    print('#  失败路径测试')
    print('#'*60)

    print('\n1. 创建新申请用于测试')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '订单系统重构',
        'system_id': 'ORDER-SYSTEM',
        'window_start': '2026-08-01T00:00:00Z',
        'window_end': '2026-08-10T23:59:59Z',
        'risk_level': 'HIGH',
        'reason': '订单系统重构'
    })
    request_id = r.json()['data']['id']

    print('\n[失败1] 非法角色操作 - 申请人尝试审批')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
        'username': 'zhangsan'
    })
    print_response('非法角色审批', r)

    print('\n[失败2] 未复核就审批')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
        'username': 'qianqi'
    })
    print_response('未复核审批', r)

    print('\n[失败3] 窗口期重叠 - 先创建一个已批准的申请')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'lisi',
        'title': '库存系统升级',
        'system_id': 'INVENTORY-SYSTEM',
        'window_start': '2026-09-01T00:00:00Z',
        'window_end': '2026-09-10T23:59:59Z',
        'risk_level': 'MEDIUM',
        'reason': '库存系统升级'
    })
    req2_id = r.json()['data']['id']
    
    requests.post(f'{BASE_URL}/requests/{req2_id}/review', json={
        'username': 'wangwu', 'approved': True
    })
    requests.post(f'{BASE_URL}/requests/{req2_id}/approve', json={
        'username': 'qianqi'
    })
    
    print('\n[失败3] 窗口期重叠 - 再创建重叠窗口的申请')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '另一个库存变更',
        'system_id': 'INVENTORY-SYSTEM',
        'window_start': '2026-09-05T00:00:00Z',
        'window_end': '2026-09-15T23:59:59Z',
        'risk_level': 'LOW',
        'reason': '另一个库存变更'
    })
    print_response('窗口重叠', r)

    print('\n[失败4] 撤回后再次生效（非已撤回状态）')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/re-effective', json={
        'username': 'qianqi'
    })
    print_response('非撤回状态再次生效', r)

    print('\n[失败5] 申请人不能复核自己的申请')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/review', json={
        'username': 'zhangsan',
        'approved': True
    })
    print_response('申请人复核自己的申请', r)

    print('\n[失败6] 无效风险等级')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '无效风险等级测试',
        'system_id': 'ORDER-SYSTEM',
        'window_start': '2026-10-01T00:00:00Z',
        'window_end': '2026-10-05T23:59:59Z',
        'risk_level': 'INVALID',
        'reason': '测试'
    })
    print_response('无效风险等级', r)

    print('\n[失败7] 无效日期格式')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '无效日期格式测试',
        'system_id': 'ORDER-SYSTEM',
        'window_start': '2026-10-01',
        'window_end': '2026-10-05',
        'risk_level': 'LOW',
        'reason': '测试'
    })
    print_response('无效日期格式', r)

def test_audit():
    print('\n' + '#'*60)
    print('#  审计记录测试')
    print('#'*60)

    print('\n1. 查询全部审计日志')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan'})
    print_response('全部审计日志', r)

    print('\n2. 查询单个申请的状态历史')
    r = requests.get(f'{BASE_URL}/requests/1/history', params={'username': 'zhangsan'})
    print_response('申请1的状态历史', r)

def test_query():
    print('\n' + '#'*60)
    print('#  查询接口测试')
    print('#'*60)

    print('\n1. 获取系统列表')
    r = requests.get(f'{BASE_URL}/systems')
    print_response('系统列表', r)

    print('\n2. 获取用户列表')
    r = requests.get(f'{BASE_URL}/users')
    print_response('用户列表', r)

    print('\n3. 获取所有申请')
    r = requests.get(f'{BASE_URL}/requests', params={'username': 'zhangsan'})
    print_response('所有申请', r)

    print('\n4. 获取单个申请详情')
    r = requests.get(f'{BASE_URL}/requests/1', params={'username': 'zhangsan'})
    print_response('申请详情', r)

if __name__ == '__main__':
    try:
        test_query()
        req1_id = test_main_flow()
        req2_id = test_withdraw_and_re_effective()
        test_failure_paths()
        test_audit()
        
        print('\n' + '#'*60)
        print('#  所有测试完成！')
        print('#'*60)
        print(f'\n主流程申请ID: {req1_id}')
        print(f'撤回测试申请ID: {req2_id}')
        print('\n请查看上方输出，验证所有流程是否正确。')
        
    except requests.exceptions.ConnectionError:
        print('错误: 无法连接到服务器，请确保服务已启动 (python run.py)')
    except Exception as e:
        print(f'测试出错: {e}')
        import traceback
        traceback.print_exc()
