import requests
import sys

BASE_URL = 'http://127.0.0.1:5000/api'


def print_result(title, success, details):
    status = "✅ 通过" if success else "❌ 失败"
    print(f'\n{status} - {title}')
    if details:
        print(f'   详情: {details}')
    return success


def verify_import_restart(batch_no=None):
    print('\n' + '#' * 70)
    print('#  重启后导入数据和审计记录验证')
    print('#' * 70)

    all_pass = True

    if not batch_no:
        print('\n从导入批次列表中获取最新批次...')
        r = requests.get(f'{BASE_URL}/import/batches', params={'username': 'zhangsan'})
        data = r.json()
        if data['success'] and len(data['data']) > 0:
            batch_no = data['data'][0]['batch_no']
            print(f'   找到最新批次: {batch_no}')
        else:
            print('错误: 未找到任何导入批次，请先运行 test_import_export.py')
            return False

    print('\n' + '=' * 70)
    print(f'  验证批次: {batch_no}')
    print('=' * 70)

    print('\n[验证1] 查询导入批次列表，重启后数据仍在')
    r = requests.get(f'{BASE_URL}/import/batches', params={'username': 'zhangsan'})
    data = r.json()
    test1 = data['success'] and len(data['data']) >= 3
    all_pass &= print_result(
        '重启后仍能查询到导入批次',
        test1,
        f'批次数量: {len(data["data"]) if data["success"] else 0}'
    )

    print('\n[验证2] 查询批次详情，所有记录仍在')
    r = requests.get(
        f'{BASE_URL}/import/batches/{batch_no}/records',
        params={'username': 'zhangsan'}
    )
    data = r.json()
    test2 = (data['success'] and
             data['data']['batch']['batch_no'] == batch_no and
             data['data']['batch']['total_count'] == 6 and
             data['data']['batch']['success_count'] == 3 and
             data['data']['batch']['fail_count'] == 3)
    all_pass &= print_result(
        '批次统计信息重启后一致',
        test2,
        f'总计: {data["data"]["batch"]["total_count"]}, 成功: {data["data"]["batch"]["success_count"]}, 失败: {data["data"]["batch"]["fail_count"]}'
    )

    if test2:
        records = data['data']['records']
        success_records = [r for r in records if r['success']]
        fail_records = [r for r in records if not r['success']]

        test2b = len(success_records) == 3 and len(fail_records) == 3
        all_pass &= print_result(
            '批次详情记录数量正确',
            test2b,
            f'成功: {len(success_records)}, 失败: {len(fail_records)}'
        )

        success_ids = [r['request_id'] for r in success_records if r['request_id']]
        print(f'   成功申请ID: {success_ids}')

    print('\n[验证3] 导入创建的申请重启后仍存在，状态正确')
    if success_ids:
        for req_id in success_ids:
            r = requests.get(
                f'{BASE_URL}/requests/{req_id}',
                params={'username': 'zhangsan'}
            )
            data = r.json()
            test3 = data['success'] and data['data']['status'] == 'PENDING_REVIEW'
            all_pass &= print_result(
                f'申请 {req_id} 重启后仍存在且状态为 PENDING_REVIEW',
                test3,
                f'状态: {data["data"]["status"] if data["success"] else "不存在"}'
            )

    print('\n[验证4] 导入创建的申请审计历史重启后仍包含批次号')
    if success_ids:
        req_id = success_ids[0]
        r = requests.get(
            f'{BASE_URL}/requests/{req_id}/history',
            params={'username': 'zhangsan'}
        )
        data = r.json()
        history = data['data']
        has_batch = any(h.get('batch') and h['batch']['batch_no'] == batch_no for h in history)
        test4 = data['success'] and has_batch
        all_pass &= print_result(
            '审计历史重启后仍包含批次号',
            test4,
            f'历史记录数: {len(history)}, 包含批次: {has_batch}'
        )

        if has_batch:
            batch_info = next(h['batch'] for h in history if h.get('batch'))
            print(f'   批次信息: {batch_info}')

    print('\n[验证5] 全量审计日志重启后仍包含导入操作记录')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan'})
    data = r.json()
    all_history = data['data']
    import_related = [h for h in all_history if h.get('batch') and h['batch']['batch_no'] == batch_no]
    test5 = len(import_related) == 3
    all_pass &= print_result(
        '全量审计日志中包含3条导入操作记录',
        test5,
        f'导入相关记录数: {len(import_related)}'
    )

    print('\n[验证6] 申请人只能看到自己导入的申请')
    r = requests.get(f'{BASE_URL}/requests', params={'username': 'lisi'})
    data = r.json()
    lisi_requests = data['data']
    lisi_ids = [req['id'] for req in lisi_requests]
    zhangsan_success_ids = set(success_ids)
    overlap = zhangsan_success_ids.intersection(set(lisi_ids))
    test6 = len(overlap) == 0
    all_pass &= print_result(
        'lisi 看不到 zhangsan 导入的申请',
        test6,
        f'lisi申请数: {len(lisi_ids)}, 重叠ID: {overlap}'
    )

    print('\n[验证7] 审批人能看到所有导入的申请')
    r = requests.get(f'{BASE_URL}/requests', params={'username': 'qianqi'})
    data = r.json()
    all_requests = data['data']
    approver_ids = [req['id'] for req in all_requests]
    has_zhangsan_imports = any(id in approver_ids for id in success_ids)
    test7 = has_zhangsan_imports
    all_pass &= print_result(
        '审批人能看到 zhangsan 导入的申请',
        test7,
        f'审批人可见数: {len(approver_ids)}, 包含导入申请: {has_zhangsan_imports}'
    )

    print('\n' + '#' * 70)
    if all_pass:
        print('#  ✅ 重启后所有导入数据和审计记录验证通过！')
    else:
        print('#  ❌ 部分验证失败，请检查上方详情')
    print('#' * 70)
    print()

    return all_pass


if __name__ == '__main__':
    try:
        batch_no = sys.argv[1] if len(sys.argv) > 1 else None
        success = verify_import_restart(batch_no)
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print('错误: 无法连接到服务器，请确保服务已启动 (python run.py)')
        exit(1)
    except Exception as e:
        print(f'验证出错: {e}')
        import traceback
        traceback.print_exc()
        exit(1)
