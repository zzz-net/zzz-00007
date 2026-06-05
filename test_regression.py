import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'

def print_result(title, success, details):
    status = "✅ 通过" if success else "❌ 失败"
    print(f'\n{status} - {title}')
    if details:
        print(f'   详情: {details}')
    return success

def get_history_count(request_id):
    r = requests.get(f'{BASE_URL}/requests/{request_id}/history', params={'username': 'zhangsan'})
    data = r.json()
    return len(data['data'])

def test_regression():
    print('\n' + '#'*70)
    print('#  回归测试：撤回后状态不变 + 审计查询过滤')
    print('#'*70)

    all_pass = True

    print('\n' + '='*70)
    print('  第一部分：创建一个申请并撤回')
    print('='*70)

    # 1. 创建新申请
    print('\n1. 创建新申请')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '回归测试撤回验证',
        'system_id': 'ORDER-SYSTEM',
        'window_start': '2026-11-01T00:00:00Z',
        'window_end': '2026-11-10T23:59:59Z',
        'risk_level': 'MEDIUM',
        'reason': '回归测试：验证撤回后不能再变更'
    })
    data = r.json()
    request_id = data['data']['id']
    print(f'   创建成功，申请ID: {request_id}')
    history_before = get_history_count(request_id)
    print(f'   当前历史记录数: {history_before}')

    # 2. 复核通过
    print('\n2. 复核通过')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/review', json={
        'username': 'wangwu',
        'approved': True
    })
    assert r.json()['success']
    print(f'   复核通过')

    # 3. 审批通过
    print('\n3. 审批通过')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
        'username': 'qianqi'
    })
    assert r.json()['success']
    print(f'   审批通过')

    # 4. 申请人撤回
    print('\n4. 申请人撤回')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/withdraw', json={
        'username': 'zhangsan',
        'comment': '回归测试撤回'
    })
    data = r.json()
    assert data['success']
    assert data['data']['status'] == 'WITHDRAWN'
    history_after_withdraw = get_history_count(request_id)
    print(f'   撤回成功，当前状态: WITHDRAWN，历史记录数: {history_after_withdraw}')

    print('\n' + '='*70)
    print('  第二部分：验证撤回后所有接口都不能修改状态')
    print('='*70)

    # 测试1: 用 re-effective 接口尝试再次批准
    print('\n[测试1] 撤回后调用 re-effective 接口')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/re-effective', json={
        'username': 'qianqi',
        'comment': '尝试再次批准'
    })
    data = r.json()
    test1_pass = (not data['success'] and 
                  data['error']['code'] == 'WITHDRAWN_FINAL_STATE' and
                  r.status_code == 400)
    all_pass &= print_result(
        're-effective 返回 WITHDRAWN_FINAL_STATE 错误',
        test1_pass,
        f'返回码: {r.status_code}, 错误码: {data.get("error", {}).get("code")}, 消息: {data.get("error", {}).get("message")}'
    )

    # 验证状态不变
    r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'zhangsan'})
    data = r.json()
    status_unchanged = data['data']['status'] == 'WITHDRAWN'
    all_pass &= print_result(
        '调用 re-effective 后状态仍为 WITHDRAWN',
        status_unchanged,
        f'当前状态: {data["data"]["status"]}'
    )

    # 验证审计历史没有增加
    history_after_test1 = get_history_count(request_id)
    history_unchanged = history_after_test1 == history_after_withdraw
    all_pass &= print_result(
        '调用 re-effective 后审计历史没有增加',
        history_unchanged,
        f'撤回后历史数: {history_after_withdraw}, 测试后历史数: {history_after_test1}'
    )

    # 测试2: 用 approve 接口尝试批准
    print('\n[测试2] 撤回后调用 approve 接口')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
        'username': 'qianqi',
        'comment': '尝试批准'
    })
    data = r.json()
    test2_pass = (not data['success'] and 
                  data['error']['code'] == 'WITHDRAWN_FINAL_STATE' and
                  r.status_code == 400)
    all_pass &= print_result(
        'approve 返回 WITHDRAWN_FINAL_STATE 错误',
        test2_pass,
        f'返回码: {r.status_code}, 错误码: {data.get("error", {}).get("code")}, 消息: {data.get("error", {}).get("message")}'
    )

    # 验证状态不变
    r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'zhangsan'})
    data = r.json()
    status_unchanged = data['data']['status'] == 'WITHDRAWN'
    all_pass &= print_result(
        '调用 approve 后状态仍为 WITHDRAWN',
        status_unchanged,
        f'当前状态: {data["data"]["status"]}'
    )

    # 验证审计历史没有增加
    history_after_test2 = get_history_count(request_id)
    history_unchanged = history_after_test2 == history_after_withdraw
    all_pass &= print_result(
        '调用 approve 后审计历史没有增加',
        history_unchanged,
        f'撤回后历史数: {history_after_withdraw}, 测试后历史数: {history_after_test2}'
    )

    # 测试3: 用 effective 接口尝试生效
    print('\n[测试3] 撤回后调用 effective 接口')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/effective', json={
        'username': 'qianqi',
        'comment': '尝试生效'
    })
    data = r.json()
    test3_pass = (not data['success'] and 
                  data['error']['code'] == 'WITHDRAWN_FINAL_STATE' and
                  r.status_code == 400)
    all_pass &= print_result(
        'effective 返回 WITHDRAWN_FINAL_STATE 错误',
        test3_pass,
        f'返回码: {r.status_code}, 错误码: {data.get("error", {}).get("code")}, 消息: {data.get("error", {}).get("message")}'
    )

    # 验证状态不变
    r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'zhangsan'})
    data = r.json()
    status_unchanged = data['data']['status'] == 'WITHDRAWN'
    all_pass &= print_result(
        '调用 effective 后状态仍为 WITHDRAWN',
        status_unchanged,
        f'当前状态: {data["data"]["status"]}'
    )

    # 验证审计历史没有增加
    history_after_test3 = get_history_count(request_id)
    history_unchanged = history_after_test3 == history_after_withdraw
    all_pass &= print_result(
        '调用 effective 后审计历史没有增加',
        history_unchanged,
        f'撤回后历史数: {history_after_withdraw}, 测试后历史数: {history_after_test3}'
    )

    print('\n' + '='*70)
    print('  第三部分：验证审计查询按 request_id 过滤')
    print('='*70)

    # 先确认有多个申请的历史
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan'})
    data = r.json()
    total_count = len(data['data'])
    print(f'\n全量审计记录数: {total_count}')

    # 测试4: 传 request_id 只返回对应申请的历史
    print('\n[测试4] 审计查询按 request_id 过滤')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': request_id})
    data = r.json()
    filtered_count = len(data['data'])
    expected_count = history_after_withdraw
    
    # 验证所有返回的记录都是对应 request_id 的
    all_match = all(h['request_id'] == request_id for h in data['data'])
    test4_pass = (data['success'] and 
                  filtered_count == expected_count and 
                  all_match and
                  filtered_count < total_count)
    all_pass &= print_result(
        '按 request_id 过滤只返回对应申请的历史',
        test4_pass,
        f'全量: {total_count}条, 过滤后: {filtered_count}条, 期望: {expected_count}条, 全部匹配request_id: {all_match}'
    )

    # 测试5: 不传 request_id 返回全量
    print('\n[测试5] 不传 request_id 返回全量历史')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan'})
    data = r.json()
    test5_pass = data['success'] and len(data['data']) == total_count
    all_pass &= print_result(
        '不传 request_id 返回全量历史',
        test5_pass,
        f'返回记录数: {len(data["data"])}, 期望: {total_count}'
    )

    # 测试6: 传非法 request_id (非整数)
    print('\n[测试6] 传非法 request_id (非整数)')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': 'abc'})
    data = r.json()
    test6_pass = (not data['success'] and 
                  data['error']['code'] == 'INVALID_REQUEST_ID' and
                  r.status_code == 400)
    all_pass &= print_result(
        '非法 request_id 返回 INVALID_REQUEST_ID 错误',
        test6_pass,
        f'返回码: {r.status_code}, 错误码: {data.get("error", {}).get("code")}'
    )

    # 测试7: 传不存在的 request_id
    print('\n[测试7] 传不存在的 request_id')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': '99999'})
    data = r.json()
    test7_pass = (not data['success'] and 
                  data['error']['code'] == 'REQUEST_NOT_FOUND' and
                  r.status_code == 404)
    all_pass &= print_result(
        '不存在的 request_id 返回 REQUEST_NOT_FOUND 错误',
        test7_pass,
        f'返回码: {r.status_code}, 错误码: {data.get("error", {}).get("code")}'
    )

    # 测试8: 传 request_id=0 (边界值)
    print('\n[测试8] 传 request_id=0 (边界值)')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': '0'})
    data = r.json()
    test8_pass = (not data['success'] and 
                  data['error']['code'] == 'REQUEST_NOT_FOUND' and
                  r.status_code == 404)
    all_pass &= print_result(
        'request_id=0 返回 REQUEST_NOT_FOUND 错误',
        test8_pass,
        f'返回码: {r.status_code}, 错误码: {data.get("error", {}).get("code")}'
    )

    # 测试9: 传空的 request_id (应该返回全量)
    print('\n[测试9] 传空的 request_id (应该返回全量)')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan', 'request_id': ''})
    data = r.json()
    test9_pass = data['success'] and len(data['data']) == total_count
    all_pass &= print_result(
        '传空 request_id 返回全量历史',
        test9_pass,
        f'返回记录数: {len(data["data"])}, 期望: {total_count}'
    )

    print('\n' + '#'*70)
    if all_pass:
        print('#  ✅ 所有回归测试通过！')
    else:
        print('#  ❌ 部分回归测试失败，请检查上方详情')
    print('#'*70)
    print()

    return all_pass

if __name__ == '__main__':
    try:
        success = test_regression()
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print('错误: 无法连接到服务器，请确保服务已启动 (python run.py)')
        exit(1)
    except Exception as e:
        print(f'测试出错: {e}')
        import traceback
        traceback.print_exc()
        exit(1)
