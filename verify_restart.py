import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'

def print_result(title, success, details):
    status = "✅ 通过" if success else "❌ 失败"
    print(f'\n{status} - {title}')
    if details:
        print(f'   详情: {details}')

def verify_data():
    print('\n' + '#'*60)
    print('#  重启后数据一致性验证')
    print('#'*60)

    all_pass = True

    print('\n1. 验证申请状态')
    r = requests.get(f'{BASE_URL}/requests/1', params={'username': 'zhangsan'})
    data = r.json()
    status = data['data']['status']
    print_result('申请1状态应为 EFFECTIVE', status == 'EFFECTIVE', f'实际状态: {status}')
    if status != 'EFFECTIVE':
        all_pass = False

    r = requests.get(f'{BASE_URL}/requests/2', params={'username': 'zhangsan'})
    data = r.json()
    status = data['data']['status']
    print_result('申请2状态应为 APPROVED', status == 'APPROVED', f'实际状态: {status}')
    if status != 'APPROVED':
        all_pass = False

    print('\n2. 验证状态历史')
    r = requests.get(f'{BASE_URL}/requests/1/history', params={'username': 'zhangsan'})
    data = r.json()
    history_count = len(data['data'])
    expected_transitions = ['PENDING_REVIEW', 'REVIEWED', 'APPROVED', 'EFFECTIVE']
    actual_transitions = [h['to_status'] for h in data['data']]
    print_result(
        f'申请1应有 {len(expected_transitions)} 条状态历史',
        history_count == len(expected_transitions) and actual_transitions == expected_transitions,
        f'实际: {history_count} 条, 转换: {actual_transitions}'
    )
    if history_count != len(expected_transitions) or actual_transitions != expected_transitions:
        all_pass = False

    r = requests.get(f'{BASE_URL}/requests/2/history', params={'username': 'zhangsan'})
    data = r.json()
    history_count = len(data['data'])
    expected_transitions = ['PENDING_REVIEW', 'REVIEWED', 'APPROVED', 'WITHDRAWN', 'APPROVED']
    actual_transitions = [h['to_status'] for h in data['data']]
    print_result(
        f'申请2应有 {len(expected_transitions)} 条状态历史',
        history_count == len(expected_transitions) and actual_transitions == expected_transitions,
        f'实际: {history_count} 条, 转换: {actual_transitions}'
    )
    if history_count != len(expected_transitions) or actual_transitions != expected_transitions:
        all_pass = False

    print('\n3. 验证窗口期冲突判断')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '验证窗口冲突',
        'system_id': 'INVENTORY-SYSTEM',
        'window_start': '2026-09-03T00:00:00Z',
        'window_end': '2026-09-07T23:59:59Z',
        'risk_level': 'LOW',
        'reason': '验证窗口冲突'
    })
    data = r.json()
    has_conflict = not data['success'] and data['error']['code'] == 'WINDOW_CONFLICT'
    print_result(
        '与已批准的申请4窗口重叠应被拒绝',
        has_conflict,
        f'返回: {data.get("error", {}).get("code", "成功")}'
    )
    if not has_conflict:
        all_pass = False

    print('\n4. 验证无效日期格式')
    r = requests.post(f'{BASE_URL}/requests', json={
        'username': 'zhangsan',
        'title': '验证日期格式',
        'system_id': 'ORDER-SYSTEM',
        'window_start': '2026-10-01',
        'window_end': '2026-10-05',
        'risk_level': 'LOW',
        'reason': '验证日期格式'
    })
    data = r.json()
    invalid_format = not data['success'] and data['error']['code'] == 'INVALID_DATETIME_FORMAT'
    print_result(
        '不完整日期格式应被拒绝',
        invalid_format,
        f'返回: {data.get("error", {}).get("code", "成功")}'
    )
    if not invalid_format:
        all_pass = False

    print('\n5. 验证完整审计日志')
    r = requests.get(f'{BASE_URL}/audit', params={'username': 'zhangsan'})
    data = r.json()
    audit_count = len(data['data'])
    print_result(
        f'审计日志应包含所有历史记录',
        audit_count >= 14,
        f'实际记录数: {audit_count}'
    )
    if audit_count < 14:
        all_pass = False

    print('\n' + '#'*60)
    if all_pass:
        print('#  ✅ 所有验证通过！重启后数据完全一致')
    else:
        print('#  ❌ 部分验证失败，请检查上方详情')
    print('#'*60)
    print()

if __name__ == '__main__':
    try:
        verify_data()
    except requests.exceptions.ConnectionError:
        print('错误: 无法连接到服务器，请确保服务已启动 (python run.py)')
    except Exception as e:
        print(f'验证出错: {e}')
        import traceback
        traceback.print_exc()
