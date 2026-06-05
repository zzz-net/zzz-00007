import requests
import json
import csv
import io
import os
import sys

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

def create_test_csv(rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['标题', '系统', '窗口开始', '窗口结束', '风险等级', '风险说明', '备注'])
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return output.getvalue()

def check_db_location():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'change_freeze.db')
    exists = os.path.exists(db_path)
    print(f'   数据库路径: {db_path}')
    print(f'   数据库存在: {exists}')
    return exists, db_path

def check_readme_consistency():
    with open('README.md', 'rb') as f:
        readme = f.read().decode('utf-8-sig', errors='ignore')
    
    checks = {
        'instance_db': 'instance/change_freeze.db' in readme,
        'csv_fields': 'CSV 字段说明' in readme,
        'csv_example': '```csv' in readme and '标题,系统,窗口开始' in readme,
        'export_curl': '/api/requests/export' in readme,
        'import_curl': '/api/requests/import' in readme,
        'batches_curl': '/api/import/batches' in readme,
        'records_curl': '/import/batches/IMP_' in readme,
        'success_response': '"batch_no": "IMP_' in readme,
        'partial_failure': 'WINDOW_CONFLICT' in readme,
        'permission_denied': 'ROLE_PERMISSION_DENIED' in readme,
        'not_withdrawn_absent': 'NOT_WITHDRAWN' not in readme,
        'withdrawn_final': 'WITHDRAWN_FINAL_STATE' in readme,
        'final_state_note': '终态' in readme,
        'batch_table': 'import_batches' in readme,
        'record_table': 'import_records' in readme,
    }
    
    all_ok = True
    for key, ok in checks.items():
        status = '✅' if ok else '❌'
        print(f'   {status} README 包含 {key}: {ok}')
        if not ok:
            all_ok = False
    
    return all_ok

def verify_restart_persistence():
    print('\n' + '='*70)
    print('  第十二部分：持久化验证 - 重启后验证')
    print('='*70)
    all_pass = True

    print('\n[测试22] 重启后验证数据库仍存在')
    db_exists_after, _ = check_db_location()
    test22 = db_exists_after
    all_pass &= test22
    print(f'   {"✅" if test22 else "❌"} 重启后数据库仍存在')

    print('\n[测试23] 重启后验证批次仍可查询')
    try:
        with open('.restart_verification.json', 'r') as f:
            saved = json.load(f)
        batch_no = saved['batch_no']
        request_id = saved['request_id']
        batch_count_before = saved['batch_count']
        history_count_before = saved['history_count']
        print(f'   已加载保存的验证信息: 批次号={batch_no}, 申请ID={request_id}')
        
        r_batch = requests.get(
            f'{BASE_URL}/import/batches/{batch_no}/records',
            params={'username': 'zhangsan'}
        )
        data = r_batch.json()
        test23 = (data['success'] and
                  data['data']['batch']['batch_no'] == batch_no and
                  len(data['data']['records']) == batch_count_before)
        all_pass &= test23
        print(f'   {"✅" if test23 else "❌"} 重启后批次仍可查询，记录数一致: {len(data["data"]["records"])} == {batch_count_before}')

        print('\n[测试24] 重启后验证审计记录仍可查询')
        r_history = requests.get(
            f'{BASE_URL}/requests/{request_id}/history',
            params={'username': 'zhangsan'}
        )
        data = r_history.json()
        test24 = (data['success'] and
                  len(data['data']) == history_count_before)
        all_pass &= test24
        print(f'   {"✅" if test24 else "❌"} 重启后审计仍可查询，记录数一致: {len(data["data"])} == {history_count_before}')

        print('\n[测试25] 重启后验证申请状态正确')
        r_req = requests.get(
            f'{BASE_URL}/requests/{request_id}',
            params={'username': 'zhangsan'}
        )
        data = r_req.json()
        test25 = (data['success'] and
                  data['data']['status'] == 'PENDING_REVIEW' and
                  data['data']['title'] == '回归导入1')
        all_pass &= test25
        print(f'   {"✅" if test25 else "❌"} 重启后申请仍可查询，状态正确: {data["data"]["status"]}')

        os.remove('.restart_verification.json')
        print(f'   💾 已清理验证信息文件')
        
    except FileNotFoundError:
        print('   ⚠️  未找到 .restart_verification.json，请先正常运行本脚本记录状态')
        all_pass = False

    return all_pass

def test_final_regression():
    print('\n' + '#'*70)
    print('#  最终回归测试：文档与接口一致性 + 导入导出全链路')
    print('#'*70)

    all_pass = True
    batch_no_for_restart = None
    restart_request_id = None

    print('\n' + '='*70)
    print('  第0部分：环境验证 - 数据库位置与 README 一致性')
    print('='*70)

    print('\n[测试0.1] 检查 SQLite 数据库位置')
    db_exists, db_path = check_db_location()
    test0_1 = db_exists
    all_pass &= test0_1
    print(f'   {"✅" if test0_1 else "❌"} 数据库文件存在于 instance/change_freeze.db')

    print('\n[测试0.2] 检查 README 文档完整性')
    test0_2 = check_readme_consistency()
    all_pass &= test0_2
    print(f'   {"✅" if test0_2 else "❌"} README 文档完整')

    if '--verify-restart' in sys.argv:
        restart_pass = verify_restart_persistence()
        all_pass &= restart_pass
        print('\n' + '#'*70)
        if all_pass:
            print('#  ✅ 所有重启验证通过！持久化完全一致！')
        else:
            print('#  ❌ 部分重启验证失败，请检查上方详情！')
        print('#'*70)
        print()
        return all_pass

    print('\n' + '='*70)
    print('  第一部分：创建申请并撤回（原有逻辑）')
    print('='*70)

    print('\n1. 创建新申请')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'lisi',
        'title': '最终回归测试',
        'system_id': 'USER-SERVICE',
        'window_start': '2029-01-01T00:00:00Z',
        'window_end': '2029-01-10T23:59:59Z',
        'risk_level': 'MEDIUM',
        'reason': '最终回归测试'
    })
    data = r.json()
    request_id = data['data']['id']
    print(f'   创建成功，申请ID: {request_id}')
    assert data['success']
    assert data['data']['status'] == 'PENDING_REVIEW'

    print('\n2. 复核通过')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/review', json={
        'username': 'zhaoliu', 'approved': True
    })
    assert r.json()['success']
    print(f'   复核通过')

    print('\n3. 审批通过')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/approve', json={
        'username': 'sunba'
    })
    assert r.json()['success']
    print(f'   审批通过')

    print('\n4. 申请人撤回')
    r = requests.post(f'{BASE_URL}/requests/{request_id}/withdraw', json={
        'username': 'lisi', 'comment': '回归测试撤回'
    })
    data = r.json()
    assert data['success']
    assert data['data']['status'] == 'WITHDRAWN'
    history_count = len(requests.get(f'{BASE_URL}/requests/{request_id}/history', 
                                     params={'username': 'lisi'}).json()['data'])
    print(f'   撤回成功，当前状态: WITHDRAWN，历史记录数: {history_count}')

    print('\n' + '='*70)
    print('  第二部分：验证撤回后三个接口都失败（原有逻辑）')
    print('='*70)

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

    r = requests.get(f'{BASE_URL}/requests/{request_id}', params={'username': 'lisi'})
    status = r.json()['data']['status']
    all_pass &= (status == 'WITHDRAWN')

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

    print('\n' + '='*70)
    print('  第三部分：验证审计查询过滤功能（原有逻辑）')
    print('='*70)

    print('\n[测试4] 审计查询按 request_id 过滤')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi', 'request_id': request_id})
    data = r.json()
    filtered = len(data['data'])
    all_match = all(h['request_id'] == request_id for h in data['data'])
    r_full = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi'})
    full_count = len(r_full.json()['data'])
    test4 = (data['success'] and filtered == history_count and all_match)
    all_pass &= test4
    print(f'   {"✅" if test4 else "❌"} 过滤正确: 过滤后{filtered}条，全部匹配request_id={request_id}: {all_match}')

    print('\n[测试5] 传非法 request_id (非整数)')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi', 'request_id': 'abc'})
    data = r.json()
    test5 = (not data['success'] and 
             data['error']['code'] == 'INVALID_REQUEST_ID' and
             r.status_code == 400)
    all_pass &= test5
    print(f'   {"✅" if test5 else "❌"} 返回 INVALID_REQUEST_ID 错误 (400)')

    print('\n[测试6] 传不存在的 request_id')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'lisi', 'request_id': '99999'})
    data = r.json()
    test6 = (not data['success'] and 
             data['error']['code'] == 'REQUEST_NOT_FOUND' and
             r.status_code == 404)
    all_pass &= test6
    print(f'   {"✅" if test6 else "❌"} 返回 REQUEST_NOT_FOUND 错误 (404)')

    print('\n' + '='*70)
    print('  第四部分：导入导出 - 申请人导入成功')
    print('='*70)

    print('\n[测试7] 申请人（zhangsan）导入合法 CSV - 全部成功')
    csv_rows = [
        ['回归导入1', 'PAYMENT-SYSTEM', '2029-02-01T00:00:00Z', '2029-02-05T23:59:59Z', 'MEDIUM', '回归测试导入1', '备注A'],
        ['回归导入2', 'ORDER-SYSTEM', '2029-02-10T00:00:00Z', '2029-02-15T23:59:59Z', 'LOW', '回归测试导入2', '备注B'],
        ['回归导入3', 'INVENTORY-SYSTEM', '2029-02-20T00:00:00Z', '2029-02-25T23:59:59Z', 'HIGH', '回归测试导入3', '备注C'],
    ]
    csv_content = create_test_csv(csv_rows)
    files = {'file': ('test_import.csv', csv_content, 'text/csv')}
    r = requests.post(
        f'{BASE_URL}/requests/import',
        files=files,
        data={'username': 'zhangsan'}
    )
    data = r.json()
    test7 = (data['success'] and
             data['data']['total_count'] == 3 and
             data['data']['success_count'] == 3 and
             data['data']['fail_count'] == 0 and
             len(data['data']['success_ids']) == 3)
    all_pass &= test7
    print(f'   {"✅" if test7 else "❌"} 申请人导入全部成功: 总计{data["data"]["total_count"]}, 成功{data["data"]["success_count"]}')

    if test7:
        batch_no_for_restart = data['data']['batch_no']
        restart_request_id = data['data']['success_ids'][0]
        print(f'   批次号（用于重启验证）: {batch_no_for_restart}')
        print(f'   申请ID（用于重启验证）: {restart_request_id}')

    print('\n[测试8] 验证导入创建的申请可查询到，且审计包含批次号')
    if restart_request_id:
        r = requests.get(f'{BASE_URL}/requests/{restart_request_id}', params={'username': 'zhangsan'})
        test8a = r.json()['success'] and r.json()['data']['title'] == '回归导入1'
        all_pass &= test8a
        print(f'   {"✅" if test8a else "❌"} 导入的申请可查询')

        r = requests.get(f'{BASE_URL}/requests/{restart_request_id}/history', params={'username': 'zhangsan'})
        history = r.json()['data']
        has_batch = any(h.get('batch') is not None for h in history)
        test8b = has_batch
        all_pass &= test8b
        print(f'   {"✅" if test8b else "❌"} 审计历史包含批次号')

    print('\n' + '='*70)
    print('  第五部分：导入导出 - 非申请人被拒')
    print('='*70)

    print('\n[测试9] 非申请人（wangwu，REVIEWER）尝试导入 - 权限拒绝')
    csv_content = create_test_csv([
        ['测试权限', 'PAYMENT-SYSTEM', '2029-03-01T00:00:00Z', '2029-03-05T23:59:59Z', 'LOW', '测试', '']
    ])
    files = {'file': ('test_perm.csv', csv_content, 'text/csv')}
    r = requests.post(
        f'{BASE_URL}/requests/import',
        files=files,
        data={'username': 'wangwu'}
    )
    data = r.json()
    test9 = (not data['success'] and
             data['error']['code'] == 'ROLE_PERMISSION_DENIED' and
             r.status_code == 403 and
             '申请人' in data['error']['message'])
    all_pass &= test9
    print(f'   {"✅" if test9 else "❌"} 非申请人导入被拒绝: {data.get("error", {}).get("code")}')

    print('\n[测试10] 非申请人（qianqi，APPROVER）尝试导入 - 权限拒绝')
    files = {'file': ('test_perm2.csv', csv_content, 'text/csv')}
    r = requests.post(
        f'{BASE_URL}/requests/import',
        files=files,
        data={'username': 'qianqi'}
    )
    data = r.json()
    test10 = (not data['success'] and
              data['error']['code'] == 'ROLE_PERMISSION_DENIED' and
              r.status_code == 403)
    all_pass &= test10
    print(f'   {"✅" if test10 else "❌"} 审批人导入被拒绝: {data.get("error", {}).get("code")}')

    print('\n' + '='*70)
    print('  第六部分：导入导出 - 窗口冲突，坏行失败但好行落库')
    print('='*70)

    print('\n[测试11] 先创建一个已批准的申请作为冲突基准')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '冲突基准申请',
        'system_id': 'PAYMENT-SYSTEM',
        'window_start': '2029-04-01T00:00:00Z',
        'window_end': '2029-04-10T23:59:59Z',
        'risk_level': 'MEDIUM',
        'reason': '冲突基准'
    })
    assert r.json()['success']
    conflict_req_id = r.json()['data']['id']
    requests.post(f'{BASE_URL}/requests/{conflict_req_id}/review', json={
        'username': 'wangwu', 'approved': True
    })
    requests.post(f'{BASE_URL}/requests/{conflict_req_id}/approve', json={
        'username': 'qianqi'
    })
    print(f'   冲突基准申请已批准，ID: {conflict_req_id}')

    print('\n[测试12] 导入包含窗口冲突的 CSV - 坏行失败，好行落库')
    csv_rows = [
        ['好行1-无冲突', 'USER-SERVICE', '2029-04-01T00:00:00Z', '2029-04-10T23:59:59Z', 'LOW', '无冲突', ''],
        ['坏行-窗口冲突', 'PAYMENT-SYSTEM', '2029-04-05T00:00:00Z', '2029-04-15T23:59:59Z', 'HIGH', '应该冲突', ''],
        ['好行2-无冲突', 'ORDER-SYSTEM', '2029-04-01T00:00:00Z', '2029-04-10T23:59:59Z', 'MEDIUM', '无冲突2', ''],
        ['好行3-无冲突', 'INVENTORY-SYSTEM', '2029-04-01T00:00:00Z', '2029-04-10T23:59:59Z', 'LOW', '无冲突3', ''],
    ]
    csv_content = create_test_csv(csv_rows)
    files = {'file': ('conflict_import.csv', csv_content, 'text/csv')}
    r = requests.post(
        f'{BASE_URL}/requests/import',
        files=files,
        data={'username': 'zhangsan'}
    )
    data = r.json()
    test12 = (data['success'] and
              data['data']['total_count'] == 4 and
              data['data']['success_count'] == 3 and
              data['data']['fail_count'] == 1)
    all_pass &= test12
    print(f'   {"✅" if test12 else "❌"} 部分失败导入: 总计{data["data"]["total_count"]}, 成功{data["data"]["success_count"]}, 失败{data["data"]["fail_count"]}')

    if test12:
        failed_rows = data['data']['failed_rows']
        conflict_code = failed_rows[0]['code']
        test12b = conflict_code == 'WINDOW_CONFLICT'
        all_pass &= test12b
        print(f'   {"✅" if test12b else "❌"} 冲突行返回 WINDOW_CONFLICT: {conflict_code}')

        success_ids = data['data']['success_ids']
        print(f'   成功的申请ID: {success_ids}')

        print('\n[测试13] 验证好行确实落库了')
        all_good_exist = True
        for req_id in success_ids:
            r = requests.get(f'{BASE_URL}/requests/{req_id}', params={'username': 'zhangsan'})
            if not r.json()['success']:
                all_good_exist = False
                break
        test13 = all_good_exist
        all_pass &= test13
        print(f'   {"✅" if test13 else "❌"} 所有好行都已落库可查询')

    print('\n' + '='*70)
    print('  第七部分：导入导出 - 导出后再导入')
    print('='*70)

    print('\n[测试14] 导出申请（审批人可见所有）')
    r = requests.get(f'{BASE_URL}/requests/export', params={'username': 'qianqi'})
    test14 = (r.status_code == 200 and 'text/csv' in r.headers['Content-Type'])
    all_pass &= test14
    print(f'   {"✅" if test14 else "❌"} 导出成功，Content-Type: {r.headers.get("Content-Type")}')

    if test14:
        exported_csv = r.content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(exported_csv))
        exported_rows = list(reader)
        print(f'   导出 {len(exported_rows)} 条记录')

        print('\n[测试15] 将导出的 CSV 再次导入（修改窗口避免冲突）')
        import_rows = []
        for i, row in enumerate(exported_rows[:3]):
            new_start = f'2029-05-{10 + i:02d}T00:00:00Z'
            new_end = f'2029-05-{15 + i:02d}T23:59:59Z'
            import_rows.append([
                f'导出再导入-{i+1}',
                row['系统'],
                new_start,
                new_end,
                row['风险等级'],
                f'导出再导入: {row["风险说明"]}',
                row.get('备注', '')
            ])

        csv_content = create_test_csv(import_rows)
        files = {'file': ('reimport.csv', csv_content, 'text/csv')}
        r = requests.post(
            f'{BASE_URL}/requests/import',
            files=files,
            data={'username': 'lisi'}
        )
        data = r.json()
        test15 = (data['success'] and
                  data['data']['total_count'] == 3 and
                  data['data']['success_count'] == 3 and
                  data['data']['fail_count'] == 0)
        all_pass &= test15
        print(f'   {"✅" if test15 else "❌"} 导出再导入全部成功: {data["data"]["success_count"]}条')

    print('\n' + '='*70)
    print('  第八部分：查询批次和明细')
    print('='*70)

    print('\n[测试16] 查询导入批次列表')
    r = requests.get(f'{BASE_URL}/import/batches', params={'username': 'zhangsan'})
    data = r.json()
    test16 = data['success'] and len(data['data']) >= 3
    all_pass &= test16
    print(f'   {"✅" if test16 else "❌"} 可查询批次列表，数量: {len(data["data"]) if data["success"] else 0}')

    print('\n[测试17] 查询批次详情（明细）')
    if batch_no_for_restart:
        r = requests.get(
            f'{BASE_URL}/import/batches/{batch_no_for_restart}/records',
            params={'username': 'zhangsan'}
        )
        data = r.json()
        test17 = (data['success'] and
                  data['data']['batch']['batch_no'] == batch_no_for_restart and
                  len(data['data']['records']) == 3)
        all_pass &= test17
        print(f'   {"✅" if test17 else "❌"} 可查询批次详情，记录数: {len(data["data"]["records"]) if data["success"] else 0}')

        if test17:
            success_records = [r for r in data['data']['records'] if r['success']]
            fail_records = [r for r in data['data']['records'] if not r['success']]
            print(f'   成功记录: {len(success_records)}条, 失败记录: {len(fail_records)}条')

    print('\n' + '='*70)
    print('  第九部分：README 文档一致性验证')
    print('='*70)

    print('\n[测试18] 验证 README 中没有 NOT_WITHDRAWN，有 WITHDRAWN_FINAL_STATE')
    with open('README.md', 'rb') as f:
        readme = f.read().decode('utf-8-sig', errors='ignore')
    
    has_not_withdrawn = 'NOT_WITHDRAWN' in readme
    has_withdrawn_final = 'WITHDRAWN_FINAL_STATE' in readme
    has_final_note = '终态' in readme
    has_instance_db = 'instance/change_freeze.db' in readme

    test18 = (not has_not_withdrawn and has_withdrawn_final and 
              has_final_note and has_instance_db)
    all_pass &= test18
    print(f'   {"✅" if not has_not_withdrawn else "❌"} 没有 NOT_WITHDRAWN: {not has_not_withdrawn}')
    print(f'   {"✅" if has_withdrawn_final else "❌"} 有 WITHDRAWN_FINAL_STATE: {has_withdrawn_final}')
    print(f'   {"✅" if has_final_note else "❌"} 有终态说明: {has_final_note}')
    print(f'   {"✅" if has_instance_db else "❌"} 有 instance/change_freeze.db: {has_instance_db}')

    print('\n' + '='*70)
    print('  第十部分：验证 API 响应与 README 示例一致')
    print('='*70)

    print('\n[测试19] 验证导入成功响应格式与 README 一致')
    if batch_no_for_restart:
        r = requests.post(
            f'{BASE_URL}/requests/import',
            files={'file': ('verify.csv', create_test_csv([
                ['验证一致性', 'USER-SERVICE', '2029-06-01T00:00:00Z', '2029-06-05T23:59:59Z', 'LOW', '验证响应格式', '']
            ]), 'text/csv')},
            data={'username': 'zhangsan'}
        )
        data = r.json()
        has_batch_no = 'batch_no' in data['data']
        has_total = 'total_count' in data['data']
        has_success = 'success_count' in data['data']
        has_fail = 'fail_count' in data['data']
        has_success_ids = 'success_ids' in data['data']
        has_failed_rows = 'failed_rows' in data['data']
        test19 = (has_batch_no and has_total and has_success and 
                  has_fail and has_success_ids and has_failed_rows)
        all_pass &= test19
        print(f'   {"✅" if test19 else "❌"} 导入响应包含所有 README 中示例的字段')

    print('\n[测试20] 验证权限拒绝响应格式与 README 一致')
    r = requests.get(f'{BASE_URL}/requests/export', params={'username': 'invalid'})
    data = r.json()
    test20 = (not data['success'] and
              'error' in data and
              'code' in data['error'] and
              'message' in data['error'])
    all_pass &= test20
    print(f'   {"✅" if test20 else "❌"} 错误响应格式与 README 一致')

    print('\n' + '='*70)
    print('  第十一部分：持久化验证 - 重启前记录状态')
    print('='*70)

    print('\n[测试21] 记录重启前的批次和审计状态')
    if batch_no_for_restart and restart_request_id:
        r_batch = requests.get(
            f'{BASE_URL}/import/batches/{batch_no_for_restart}/records',
            params={'username': 'zhangsan'}
        )
        batch_before = r_batch.json()
        
        r_history = requests.get(
            f'{BASE_URL}/requests/{restart_request_id}/history',
            params={'username': 'zhangsan'}
        )
        history_before = r_history.json()
        
        batch_count_before = len(batch_before['data']['records'])
        history_count_before = len(history_before['data'])
        
        print(f'   重启前批次记录数: {batch_count_before}')
        print(f'   重启前审计记录数: {history_count_before}')
        print(f'   批次号: {batch_no_for_restart}')
        print(f'   申请ID: {restart_request_id}')
        
        print(f'\n   ⚠️  请保存以上信息用于重启后验证')
        print(f'   ⚠️  现在请手动重启服务 (Ctrl+C 后重新运行 python run.py)')
        print(f'   ⚠️  重启后再次运行本脚本验证持久化')
        
        with open('.restart_verification.json', 'w') as f:
            json.dump({
                'batch_no': batch_no_for_restart,
                'request_id': restart_request_id,
                'batch_count': batch_count_before,
                'history_count': history_count_before
            }, f, indent=2)
        print(f'   💾 已保存验证信息到 .restart_verification.json')

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
