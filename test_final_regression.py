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

def test_final_regression():
    print('\n' + '#'*70)
    print('#  最终回归测试：文档与接口一致性验证')
    print('#'*70)

    all_pass = True

    print('\n' + '='*70)
    print('  第一部分：创建申请并撤回')
    print('='*70)

    # 1. 创建新申请
    print('\n1. 创建新申请')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'lisi',
        'title': '最终回归测试',
        'system_id': 'USER-SERVICE',
        'window_start': '2027-01-01T00:00:00Z',
        'window_end': '2027-01-10T23:59:59Z',
        'risk_level': 'MEDIUM',
        'reason': '最终回归测试'
    })
    data = r.json()
    request_id = data['data']['id']
    print(f'   创建成功，申请ID: {request_id}')
    assert data['success']
    assert data['data']['status'] == 'PENDING_REVIEW'

    # 2. 复核通过
    print('\n2. 复核通过')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/review', json={
        'username': 'zhaoliu', 'approved': True
    })
    assert r.json()['success']
    print(f'   复核通过')

    # 3. 审批通过
    print('\n3. 审批通过')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
        'username': 'sunba'
    })
    assert r.json()['success']
    print(f'   审批通过')

    # 4. 申请人撤回
    print('\n4. 申请人撤回')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/withdraw', json={
        'username': 'lisi', 'comment': '回归测试撤回'
    })
    data = r.json()
    assert data['success']
    assert data['data']['status'] == 'WITHDRAWN'
    history_count = len(r.json()['data'].get('status_history', [])) or \
                    len(requests.get(f'{BASE_URL}/requests/{request_id}/history', 
                                     params={'username': 'lisi'}).json()['data'])
    print(f'   撤回成功，当前状态: WITHDRAWN，历史记录数: {history_count}')

    print('\n' + '='*70)
    print('  第二部分：验证撤回后三个接口都失败，状态和审计不变')
    print('='*70)

    # 测试1: 撤回后调用 re-effective
    print('\n[测试1] 撤回后调用 re-effective 接口')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/re-effective', json={
        'username': 'sunba', 'comment': '尝试再次批准'
    })
    data = r.json()
    test1 = (not data['success'] and 
             data['error']['code'] == 'WITHDRAWN_FINAL_STATE' and
             r.status_code == 400 and
             '终态' in data['error']['message'])
    all_pass &= test1
    print(f'   {"✅" if test1 else "❌"} 返回 WITHDRAWN_FINAL_STATE 错误')

    # 验证状态不变
    r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'lisi'})
    status = r.json()['data']['status']
    test1b = status == 'WITHDRAWN'
    all_pass &= test1b
    print(f'   {"✅" if test1b else "❌"} 状态保持 WITHDRAWN: {status}')

    # 验证审计不变
    r = requests.get(f'{BASE_URL}/requests/{request_id}/history', params={'username': 'lisi'})
    new_count = len(r.json()['data'])
    test1c = new_count == history_count
    all_pass &= test1c
    print(f'   {"✅" if test1c else "❌"} 审计历史不变: {history_count} -> {new_count}')

    # 测试2: 撤回后调用 approve
    print('\n[测试2] 撤回后调用 approve 接口')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
        'username': 'sunba', 'comment': '尝试批准'
    })
    data = r.json()
    test2 = (not data['success'] and 
             data['error']['code'] == 'WITHDRAWN_FINAL_STATE' and
             r.status_code == 400)
    all_pass &= test2
    print(f'   {"✅" if test2 else "❌"} 返回 WITHDRAWN_FINAL_STATE 错误')

    # 验证状态不变
    r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'lisi'})
    status = r.json()['data']['status']
    test2b = status == 'WITHDRAWN'
    all_pass &= test2b
    print(f'   {"✅" if test2b else "❌"} 状态保持 WITHDRAWN: {status}')

    # 验证审计不变
    r = requests.get(f'{BASE_URL}/requests/{request_id}/history', params={'username': 'lisi'})
    new_count = len(r.json()['data'])
    test2c = new_count == history_count
    all_pass &= test2c
    print(f'   {"✅" if test2c else "❌"} 审计历史不变: {history_count} -> {new_count}')

    # 测试3: 撤回后调用 effective
    print('\n[测试3] 撤回后调用 effective 接口')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/effective', json={
        'username': 'sunba', 'comment': '尝试生效'
    })
    data = r.json()
    test3 = (not data['success'] and 
             data['error']['code'] == 'WITHDRAWN_FINAL_STATE' and
             r.status_code == 400)
    all_pass &= test3
    print(f'   {"✅" if test3 else "❌"} 返回 WITHDRAWN_FINAL_STATE 错误')

    # 验证状态不变
    r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'lisi'})
    status = r.json()['data']['status']
    test3b = status == 'WITHDRAWN'
    all_pass &= test3b
    print(f'   {"✅" if test3b else "❌"} 状态保持 WITHDRAWN: {status}')

    # 验证审计不变
    r = requests.get(f'{BASE_URL}/requests/{request_id}/history', params={'username': 'lisi'})
    new_count = len(r.json()['data'])
    test3c = new_count == history_count
    all_pass &= test3c
    print(f'   {"✅" if test3c else "❌"} 审计历史不变: {history_count} -> {new_count}')

    print('\n' + '='*70)
    print('  第三部分：验证审计查询过滤功能')
    print('='*70)

    # 测试4: 传 request_id 只返回对应申请的历史
    print('\n[测试4] 审计查询按 request_id 过滤')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi', 'request_id': request_id})
    data = r.json()
    filtered = len(data['data'])
    all_match = all(h['request_id'] == request_id for h in data['data'])
    
    # 获取全量
    r_full = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi'})
    full_count = len(r_full.json()['data'])
    
    test4 = (data['success'] and filtered == history_count and 
             all_match and filtered < full_count)
    all_pass &= test4
    print(f'   {"✅" if test4 else "❌"} 过滤正确: 全量{full_count}条 -> 过滤后{filtered}条，全部匹配request_id={request_id}: {all_match}')

    # 测试5: 不传 request_id 返回全量
    print('\n[测试5] 不传 request_id 返回全量')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi'})
    data = r.json()
    test5 = data['success'] and len(data['data']) == full_count
    all_pass &= test5
    print(f'   {"✅" if test5 else "❌"} 返回全量: {len(data["data"])}条')

    # 测试6: 传非法 request_id (非整数)
    print('\n[测试6] 传非法 request_id (非整数)')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi', 'request_id': 'abc'})
    data = r.json()
    test6 = (not data['success'] and 
             data['error']['code'] == 'INVALID_REQUEST_ID' and
             r.status_code == 400)
    all_pass &= test6
    print(f'   {"✅" if test6 else "❌"} 返回 INVALID_REQUEST_ID 错误 (400)')

    # 测试7: 传不存在的 request_id
    print('\n[测试7] 传不存在的 request_id')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi', 'request_id': '99999'})
    data = r.json()
    test7 = (not data['success'] and 
             data['error']['code'] == 'REQUEST_NOT_FOUND' and
             r.status_code == 404)
    all_pass &= test7
    print(f'   {"✅" if test7 else "❌"} 返回 REQUEST_NOT_FOUND 错误 (404)')

    # 测试8: 传空 request_id 返回全量
    print('\n[测试8] 传空 request_id 返回全量')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi', 'request_id': ''})
    data = r.json()
    test8 = data['success'] and len(data['data']) == full_count
    all_pass &= test8
    print(f'   {"✅" if test8 else "❌"} 返回全量: {len(data["data"])}条')

    print('\n' + '='*70)
    print('  第四部分：验证文档中删除了 NOT_WITHDRAWN 和撤回后批准示例')
    print('='*70)

    # 检查 README 中没有 NOT_WITHDRAWN
    print('\n[测试9] 检查 README 一致性')
    with open('README.md', 'r', encoding='utf-8') as f:
        readme = f.read()
    
    has_not_withdrawn = 'NOT_WITHDRAWN' in readme
    has_withdrawn_final = 'WITHDRAWN_FINAL_STATE' in readme
    has_re_approve_example = '撤回后再次批准' in readme and '```bash' in readme.split('撤回后再次批准')[0][-50:]
    has_audit_filter = '/api/audit?username=...&request_id=...' in readme
    has_final_note = '终态' in readme

    print(f'   {"✅" if not has_not_withdrawn else "❌"} README 中没有 NOT_WITHDRAWN: {not has_not_withdrawn}')
    print(f'   {"✅" if has_withdrawn_final else "❌"} README 中有 WITHDRAWN_FINAL_STATE: {has_withdrawn_final}')
    print(f'   {"✅" if has_audit_filter else "❌"} README 中有审计过滤示例: {has_audit_filter}')
    print(f'   {"✅" if has_final_note else "❌"} README 中有终态说明: {has_final_note}')
    
    all_pass &= (not has_not_withdrawn and has_withdrawn_final and 
                 has_audit_filter and has_final_note)

    # 检查 init_db 中审批人说明
    with open('init_db.py', 'r', encoding='utf-8') as f:
        init_db = f.read()
    
    has_correct_approver = '撤回是终态，不可再变更' in init_db
    has_old_approver = '再次批准撤回的申请' in init_db
    print(f'   {"✅" if has_correct_approver else "❌"} init_db 审批人说明正确: {has_correct_approver}')
    print(f'   {"✅" if not has_old_approver else "❌"} init_db 没有旧说明: {not has_old_approver}')
    
    all_pass &= (has_correct_approver and not has_old_approver)

    print('\n' + '#'*70)
    if all_pass:
        print('#  ✅ 所有回归测试通过！文档与接口完全一致！')
    else:
        print('#  ❌ 部分回归测试失败，请检查上方详情！')
    print('#'*70)
    print()

    return all_pass

if __name__ == '__main__':
    try:
        success = test_final_regression()
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print('错误: 无法连接到服务器，请确保服务已启动 (python run.py)')
        exit(1)
    except Exception as e:
        print(f'测试出错: {e}')
        import traceback
        traceback.print_exc()
        exit(1)
