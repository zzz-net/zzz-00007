import requests
import csv
import io
import json

BASE_URL = 'http://127.0.0.1:5000/api'


def print_result(title, success, details):
    status = "✅ 通过" if success else "❌ 失败"
    print(f'\n{status} - {title}')
    if details:
        print(f'   详情: {details}')
    return success


def create_test_csv(rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['标题', '系统', '窗口开始', '窗口结束', '风险等级', '风险说明', '备注'])
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return output.getvalue()


def test_import_export():
    print('\n' + '#' * 70)
    print('#  导入导出功能回归测试')
    print('#' * 70)

    all_pass = True
    batch_no_to_verify = None
    import_success_ids = []

    print('\n' + '=' * 70)
    print('  第一部分：权限拦截测试')
    print('=' * 70)

    print('\n[测试1] 无权限用户（REVIEWER）尝试导入')
    csv_content = create_test_csv([
        ['测试导入1', 'PAYMENT-SYSTEM', '2026-06-20T00:00:00Z', '2026-06-25T23:59:59Z', 'LOW', '测试导入', '备注1']
    ])
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    r = requests.post(
        f'{BASE_URL}/requests/import',
        files=files,
        data={'username': 'wangwu'}
    )
    data = r.json()
    test1 = (not data['success'] and
             data['error']['code'] == 'ROLE_PERMISSION_DENIED' and
             r.status_code == 403)
    all_pass &= print_result(
        'REVIEWER 导入被拒绝',
        test1,
        f'返回码: {r.status_code}, 错误码: {data.get("error", {}).get("code")}'
    )

    print('\n[测试2] 无权限用户（无角色）尝试导出')
    r = requests.get(f'{BASE_URL}/requests/export', params={'username': 'invalid_user'})
    data = r.json()
    test2 = (not data['success'] and
             data['error']['code'] == 'USER_NOT_FOUND' and
             r.status_code == 403)
    all_pass &= print_result(
        '不存在的用户导出被拒绝',
        test2,
        f'返回码: {r.status_code}, 错误码: {data.get("error", {}).get("code")}'
    )

    print('\n[测试3] 缺少 username 参数导出')
    r = requests.get(f'{BASE_URL}/requests/export')
    data = r.json()
    test3 = (not data['success'] and
             data['error']['code'] == 'MISSING_USERNAME')
    all_pass &= print_result(
        '缺少 username 导出被拒绝',
        test3,
        f'错误码: {data.get("error", {}).get("code")}'
    )

    print('\n' + '=' * 70)
    print('  第二部分：先创建一些申请用于导出测试')
    print('=' * 70)

    print('\n创建申请1（zhangsan）')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '导出测试申请1',
        'system_id': 'PAYMENT-SYSTEM',
        'window_start': '2026-06-10T00:00:00Z',
        'window_end': '2026-06-15T23:59:59Z',
        'risk_level': 'MEDIUM',
        'reason': '导出测试用申请1',
        'remark': '备注信息1'
    })
    assert r.json()['success']
    req1_id = r.json()['data']['id']
    print(f'   申请1 ID: {req1_id}')

    print('\n创建申请2（lisi）')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'lisi',
        'title': '导出测试申请2',
        'system_id': 'USER-SERVICE',
        'window_start': '2026-07-01T00:00:00Z',
        'window_end': '2026-07-05T23:59:59Z',
        'risk_level': 'LOW',
        'reason': '导出测试用申请2',
        'remark': '备注信息2'
    })
    assert r.json()['success']
    req2_id = r.json()['data']['id']
    print(f'   申请2 ID: {req2_id}')

    print('\n' + '=' * 70)
    print('  第三部分：导出测试 - 用户可见性过滤')
    print('=' * 70)

    print('\n[测试4] APPLICANT（zhangsan）导出 - 只能看到自己的申请')
    r = requests.get(f'{BASE_URL}/requests/export', params={'username': 'zhangsan'})
    test4 = (r.status_code == 200 and
             'text/csv' in r.headers['Content-Type'])
    all_pass &= print_result(
        'zhangsan 导出成功',
        test4,
        f'状态码: {r.status_code}, Content-Type: {r.headers.get("Content-Type")}'
    )

    if test4:
        content = r.content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        zhangsan_count = len(rows)
        all_zhangsan = all('导出测试申请1' in row['标题'] for row in rows)
        print(f'   zhangsan 导出 {zhangsan_count} 条记录，全部是自己的: {all_zhangsan}')

        test4b = zhangsan_count >= 1 and all_zhangsan
        all_pass &= print_result(
            'zhangsan 只能看到自己的申请',
            test4b,
            f'导出条数: {zhangsan_count}'
        )

    print('\n[测试5] APPROVER（qianqi）导出 - 能看到所有申请')
    r = requests.get(f'{BASE_URL}/requests/export', params={'username': 'qianqi'})
    test5 = (r.status_code == 200 and
             'text/csv' in r.headers['Content-Type'])
    all_pass &= print_result(
        'qianqi 导出成功',
        test5,
        f'状态码: {r.status_code}'
    )

    if test5:
        content = r.content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        approver_count = len(rows)
        print(f'   qianqi 导出 {approver_count} 条记录')

        test5b = approver_count > zhangsan_count
        all_pass &= print_result(
            '审批人能看到比申请人更多的申请',
            test5b,
            f'审批人: {approver_count}条, 申请人: {zhangsan_count}条'
        )

    print('\n' + '=' * 70)
    print('  第四部分：导入测试 - 部分失败场景')
    print('=' * 70)

    print('\n[测试6] 导入CSV - 包含合法行和非法行（部分失败）')
    csv_rows = [
        ['合法导入1', 'PAYMENT-SYSTEM', '2026-08-01T00:00:00Z', '2026-08-05T23:59:59Z', 'MEDIUM', '合法导入测试1', '备注A'],
        ['系统不存在', 'INVALID-SYSTEM', '2026-08-10T00:00:00Z', '2026-08-15T23:59:59Z', 'LOW', '系统不存在测试', '备注B'],
        ['合法导入2', 'ORDER-SYSTEM', '2026-09-01T00:00:00Z', '2026-09-05T23:59:59Z', 'HIGH', '合法导入测试2', '备注C'],
        ['风险等级无效', 'INVENTORY-SYSTEM', '2026-10-01T00:00:00Z', '2026-10-05T23:59:59Z', 'INVALID', '风险等级无效测试', '备注D'],
        ['窗口格式错误', 'USER-SERVICE', '2026-10-01', '2026-10-05', 'LOW', '日期格式错误测试', '备注E'],
        ['合法导入3', 'INVENTORY-SYSTEM', '2026-11-01T00:00:00Z', '2026-11-05T23:59:59Z', 'LOW', '合法导入测试3', '备注F'],
    ]

    csv_content = create_test_csv(csv_rows)
    files = {'file': ('test_import.csv', csv_content, 'text/csv')}
    r = requests.post(
        f'{BASE_URL}/requests/import',
        files=files,
        data={'username': 'zhangsan'}
    )
    data = r.json()

    test6 = (data['success'] and
             data['data']['total_count'] == 6 and
             data['data']['success_count'] == 3 and
             data['data']['fail_count'] == 3)
    all_pass &= print_result(
        '部分失败导入 - 成功3条，失败3条',
        test6,
        f'总计: {data["data"]["total_count"]}, 成功: {data["data"]["success_count"]}, 失败: {data["data"]["fail_count"]}'
    )

    if test6:
        batch_no_to_verify = data['data']['batch_no']
        import_success_ids = data['data']['success_ids']
        failed_rows = data['data']['failed_rows']

        print(f'   批次号: {batch_no_to_verify}')
        print(f'   成功申请ID: {import_success_ids}')
        print(f'   失败行: {failed_rows}')

        failed_codes = [f['code'] for f in failed_rows]
        expected_codes = {'SYSTEM_NOT_FOUND', 'INVALID_RISK_LEVEL', 'INVALID_DATETIME_FORMAT'}
        test6b = expected_codes.issubset(set(failed_codes))
        all_pass &= print_result(
            '失败行包含预期的错误码',
            test6b,
            f'实际错误码: {failed_codes}, 期望包含: {expected_codes}'
        )

        failed_row_nums = [f['row'] for f in failed_rows]
        test6c = sorted(failed_row_nums) == [3, 5, 6]
        all_pass &= print_result(
            '失败行号正确（第3、5、6行）',
            test6c,
            f'失败行号: {sorted(failed_row_nums)}'
        )

    print('\n' + '=' * 70)
    print('  第五部分：导入测试 - 窗口冲突')
    print('=' * 70)

    print('\n[测试7] 先创建一个已批准的申请用于冲突测试')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '冲突测试基准申请',
        'system_id': 'PAYMENT-SYSTEM',
        'window_start': '2026-12-01T00:00:00Z',
        'window_end': '2026-12-10T23:59:59Z',
        'risk_level': 'MEDIUM',
        'reason': '窗口冲突测试基准'
    })
    assert r.json()['success']
    conflict_req_id = r.json()['data']['id']
    print(f'   基准申请ID: {conflict_req_id}')

    requests.post(f'{BASE_URL}/requests/{conflict_req_id}/review', json={
        'username': 'wangwu', 'approved': True
    })
    requests.post(f'{BASE_URL}/requests/{conflict_req_id}/approve', json={
        'username': 'qianqi'
    })
    print('   基准申请已批准')

    print('\n[测试8] 导入包含窗口冲突的CSV')
    csv_rows = [
        ['无冲突申请', 'USER-SERVICE', '2026-12-01T00:00:00Z', '2026-12-10T23:59:59Z', 'LOW', '无冲突', ''],
        ['窗口冲突申请', 'PAYMENT-SYSTEM', '2026-12-05T00:00:00Z', '2026-12-15T23:59:59Z', 'HIGH', '窗口应该冲突', ''],
        ['另一个无冲突', 'ORDER-SYSTEM', '2026-12-01T00:00:00Z', '2026-12-10T23:59:59Z', 'MEDIUM', '无冲突2', ''],
    ]

    csv_content = create_test_csv(csv_rows)
    files = {'file': ('conflict_test.csv', csv_content, 'text/csv')}
    r = requests.post(
        f'{BASE_URL}/requests/import',
        files=files,
        data={'username': 'zhangsan'}
    )
    data = r.json()

    test8 = (data['success'] and
             data['data']['total_count'] == 3 and
             data['data']['success_count'] == 2 and
             data['data']['fail_count'] == 1)
    all_pass &= print_result(
        '窗口冲突导入 - 成功2条，冲突1条',
        test8,
        f'总计: {data["data"]["total_count"]}, 成功: {data["data"]["success_count"]}, 失败: {data["data"]["fail_count"]}'
    )

    if test8:
        failed_rows = data['data']['failed_rows']
        conflict_code = failed_rows[0]['code']
        test8b = conflict_code == 'WINDOW_CONFLICT'
        all_pass &= print_result(
            '冲突行返回 WINDOW_CONFLICT 错误码',
            test8b,
            f'错误码: {conflict_code}, 行号: {failed_rows[0]["row"]}'
        )

    print('\n' + '=' * 70)
    print('  第六部分：导出再导入')
    print('=' * 70)

    print('\n[测试9] 导出审批人可见的所有申请')
    r = requests.get(f'{BASE_URL}/requests/export', params={'username': 'qianqi'})
    assert r.status_code == 200
    exported_csv = r.content.decode('utf-8-sig')
    exported_reader = csv.DictReader(io.StringIO(exported_csv))
    exported_rows = list(exported_reader)
    print(f'   导出 {len(exported_rows)} 条记录')

    print('\n[测试10] 将导出的CSV再次导入（修改窗口避免冲突）')
    import_rows = []
    for i, row in enumerate(exported_rows[:3]):
        new_start = f'2027-01-{10 + i:02d}T00:00:00Z'
        new_end = f'2027-01-{15 + i:02d}T23:59:59Z'
        import_rows.append([
            f'导入导出测试-{i+1}',
            row['系统'],
            new_start,
            new_end,
            row['风险等级'],
            f'导出再导入测试: {row["风险说明"]}',
            row['备注']
        ])

    csv_content = create_test_csv(import_rows)
    files = {'file': ('reimport.csv', csv_content, 'text/csv')}
    r = requests.post(
        f'{BASE_URL}/requests/import',
        files=files,
        data={'username': 'lisi'}
    )
    data = r.json()

    test10 = (data['success'] and
              data['data']['total_count'] == 3 and
              data['data']['success_count'] == 3 and
              data['data']['fail_count'] == 0)
    all_pass &= print_result(
        '导出再导入全部成功',
        test10,
        f'总计: {data["data"]["total_count"]}, 成功: {data["data"]["success_count"]}'
    )

    if test10:
        batch_no_for_reimport = data['data']['batch_no']
        print(f'   批次号: {batch_no_for_reimport}')

    print('\n' + '=' * 70)
    print('  第七部分：审计历史和批次追踪')
    print('=' * 70)

    print('\n[测试11] 查看导入创建的申请的审计历史，应包含批次号')
    if import_success_ids:
        req_id = import_success_ids[0]
        r = requests.get(
            f'{BASE_URL}/requests/{req_id}/history',
            params={'username': 'zhangsan'}
        )
        data = r.json()
        history = data['data']
        has_batch = any(h.get('batch') is not None for h in history)
        test11 = data['success'] and has_batch
        all_pass &= print_result(
            '导入创建的申请审计历史包含批次号',
            test11,
            f'历史记录数: {len(history)}, 包含批次: {has_batch}'
        )

        if has_batch:
            batch_info = next(h['batch'] for h in history if h.get('batch'))
            print(f'   批次信息: {batch_info}')

    print('\n[测试12] 查询导入批次列表')
    r = requests.get(f'{BASE_URL}/import/batches', params={'username': 'zhangsan'})
    data = r.json()
    test12 = data['success'] and len(data['data']) >= 2
    all_pass &= print_result(
        '可查询到导入批次列表',
        test12,
        f'批次数量: {len(data["data"]) if data["success"] else 0}'
    )

    print('\n[测试13] 查询批次详情记录')
    if batch_no_to_verify:
        r = requests.get(
            f'{BASE_URL}/import/batches/{batch_no_to_verify}/records',
            params={'username': 'zhangsan'}
        )
        data = r.json()
        test13 = (data['success'] and
                  data['data']['batch']['batch_no'] == batch_no_to_verify and
                  len(data['data']['records']) == 6)
        all_pass &= print_result(
            '可查询批次详情，包含每行结果',
            test13,
            f'批次号: {data["data"]["batch"]["batch_no"]}, 记录数: {len(data["data"]["records"])}'
        )

        if test13:
            success_records = [r for r in data['data']['records'] if r['success']]
            fail_records = [r for r in data['data']['records'] if not r['success']]
            print(f'   成功记录: {len(success_records)}条, 失败记录: {len(fail_records)}条')

    print('\n' + '=' * 70)
    print('  第八部分：用户可见性验证（申请人只能看到自己的申请）')
    print('=' * 70)

    print('\n[测试14] zhangsan 查询申请列表')
    r = requests.get(f'{BASE_URL}/requests', params={'username': 'zhangsan'})
    data = r.json()
    zhangsan_requests = data['data']
    all_zhangsan = all(req['applicant']['username'] == 'zhangsan' for req in zhangsan_requests)
    test14 = data['success'] and all_zhangsan
    all_pass &= print_result(
        'zhangsan 只能看到自己的申请',
        test14,
        f'申请数量: {len(zhangsan_requests)}, 全部是zhangsan的: {all_zhangsan}'
    )

    print('\n[测试15] qianqi（审批人）查询申请列表')
    r = requests.get(f'{BASE_URL}/requests', params={'username': 'qianqi'})
    data = r.json()
    all_requests = data['data']
    has_others = any(req['applicant']['username'] != 'qianqi' for req in all_requests)
    test15 = data['success'] and has_others and len(all_requests) > len(zhangsan_requests)
    all_pass &= print_result(
        '审批人能看到所有申请',
        test15,
        f'申请数量: {len(all_requests)}, 包含其他人的: {has_others}'
    )

    print('\n' + '#' * 70)
    if all_pass:
        print('#  ✅ 所有导入导出回归测试通过！')
    else:
        print('#  ❌ 部分测试失败，请检查上方详情')
    print('#' * 70)
    print()

    return all_pass, batch_no_to_verify


if __name__ == '__main__':
    try:
        success, batch_no = test_import_export()
        if batch_no:
            print(f'=== 需要在重启后验证的批次号: {batch_no} ===')
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print('错误: 无法连接到服务器，请确保服务已启动 (python run.py)')
        exit(1)
    except Exception as e:
        print(f'测试出错: {e}')
        import traceback
        traceback.print_exc()
        exit(1)
