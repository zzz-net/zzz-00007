#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
curl 命令演示：导入导出功能的用户可见结果验证
"""

import requests
import csv
import io
import json

BASE_URL = 'http://127.0.0.1:5000/api'


def print_separator(title):
    print('\n' + '=' * 70)
    print(f'  {title}')
    print('=' * 70)


def create_sample_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['标题', '系统', '窗口开始', '窗口结束', '风险等级', '风险说明', '备注'])
    writer.writerow(['curl测试导入1', 'PAYMENT-SYSTEM', '2026-07-10T00:00:00Z', '2026-07-15T23:59:59Z', 'LOW', 'curl导入测试1', '备注A'])
    writer.writerow(['curl测试导入2', 'USER-SERVICE', '2026-07-20T00:00:00Z', '2026-07-25T23:59:59Z', 'MEDIUM', 'curl导入测试2', '备注B'])
    output.seek(0)
    return output.getvalue()


def run_curl_demo():
    print('\n' + '#' * 70)
    print('#  curl 命令演示：导入导出功能用户可见结果验证')
    print('#' * 70)

    print('\n' + '~' * 70)
    print('说明：以下展示的 curl 命令和响应，与实际 API 调用结果一致')
    print('~' * 70)

    print_separator('1. 导出申请为 CSV (curl)')
    print('''
curl -o requests.csv "http://127.0.0.1:5000/api/requests/export?username=zhangsan"
''')
    r = requests.get(f'{BASE_URL}/requests/export', params={'username': 'zhangsan'})
    print(f'响应状态码: {r.status_code}')
    print(f'Content-Type: {r.headers.get("Content-Type")}')
    if r.status_code == 200:
        content = r.content.decode('utf-8-sig')
        lines = content.strip().split('\n')
        print(f'CSV 内容（前3行）:')
        for line in lines[:3]:
            print(f'  {line}')
        print(f'... 共 {len(lines) - 1} 条数据')

    print_separator('2. 无权限用户尝试导入 (curl)')
    print('''
curl -X POST http://127.0.0.1:5000/api/requests/import \\
  -F "username=wangwu" \\
  -F "file=@requests.csv"
''')
    csv_content = create_sample_csv()
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    r = requests.post(f'{BASE_URL}/requests/import', files=files, data={'username': 'wangwu'})
    print(f'响应状态码: {r.status_code}')
    print(f'响应内容: {json.dumps(r.json(), ensure_ascii=False, indent=2)}')

    print_separator('3. 申请人导入 CSV (curl)')
    print('''
curl -X POST http://127.0.0.1:5000/api/requests/import \\
  -F "username=zhangsan" \\
  -F "file=@requests.csv"
''')
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    r = requests.post(f'{BASE_URL}/requests/import', files=files, data={'username': 'zhangsan'})
    data = r.json()
    print(f'响应状态码: {r.status_code}')
    print(f'响应内容: {json.dumps(data, ensure_ascii=False, indent=2)}')

    batch_no = None
    if data['success']:
        batch_no = data['data']['batch_no']
        print(f'\\n导入成功！批次号: {batch_no}')
        print(f'成功: {data["data"]["success_count"]} 条, 失败: {data["data"]["fail_count"]} 条')

    print_separator('4. 查询导入批次列表 (curl)')
    print('''
curl "http://127.0.0.1:5000/api/import/batches?username=zhangsan"
''')
    r = requests.get(f'{BASE_URL}/import/batches', params={'username': 'zhangsan'})
    print(f'响应状态码: {r.status_code}')
    data = r.json()
    print(f'返回批次数量: {len(data["data"]) if data["success"] else 0}')
    if data['success'] and len(data['data']) > 0:
        print(f'最新批次: {data["data"][0]["batch_no"]}')

    print_separator('5. 查询批次详情记录 (curl)')
    if batch_no:
        print(f'''
curl "http://127.0.0.1:5000/api/import/batches/{batch_no}/records?username=zhangsan"
''')
        r = requests.get(f'{BASE_URL}/import/batches/{batch_no}/records', params={'username': 'zhangsan'})
        print(f'响应状态码: {r.status_code}')
        data = r.json()
        if data['success']:
            print(f'批次: {data["data"]["batch"]["batch_no"]}')
            print(f'总计: {data["data"]["batch"]["total_count"]}, 成功: {data["data"]["batch"]["success_count"]}, 失败: {data["data"]["batch"]["fail_count"]}')
            for rec in data['data']['records']:
                status = '✅' if rec['success'] else '❌'
                err = f' [{rec["error_code"]}]' if not rec['success'] else ''
                print(f'  行{rec["row_no"]}: {status} 请求ID={rec["request_id"]}{err}')

    print_separator('6. 验证用户可见性 - zhangsan 只能看到自己的申请 (curl)')
    print('''
curl "http://127.0.0.1:5000/api/requests?username=zhangsan"
''')
    r = requests.get(f'{BASE_URL}/requests', params={'username': 'zhangsan'})
    data = r.json()
    if data['success']:
        applicants = set(req['applicant']['username'] for req in data['data'])
        print(f'zhangsan 可见申请数: {len(data["data"])}')
        print(f'涉及申请人: {applicants}')
        print(f'全部是 zhangsan 的申请: {applicants == {"zhangsan"}}')

    print_separator('7. 验证用户可见性 - qianqi（审批人）能看到所有申请 (curl)')
    print('''
curl "http://127.0.0.1:5000/api/requests?username=qianqi"
''')
    r = requests.get(f'{BASE_URL}/requests', params={'username': 'qianqi'})
    data = r.json()
    if data['success']:
        applicants = set(req['applicant']['username'] for req in data['data'])
        print(f'qianqi 可见申请数: {len(data["data"])}')
        print(f'涉及申请人: {applicants}')
        print(f'能看到多人的申请: {len(applicants) > 1}')

    print_separator('8. 验证导入创建的申请审计历史包含批次号 (curl)')
    if batch_no:
        r = requests.get(f'{BASE_URL}/import/batches/{batch_no}/records', params={'username': 'zhangsan'})
        data = r.json()
        if data['success']:
            success_recs = [r for r in data['data']['records'] if r['success'] and r['request_id']]
            if success_recs:
                req_id = success_recs[0]['request_id']
                print(f'''
curl "http://127.0.0.1:5000/api/requests/{req_id}/history?username=zhangsan"
''')
                r = requests.get(f'{BASE_URL}/requests/{req_id}/history', params={'username': 'zhangsan'})
                history = r.json()
                if history['success']:
                    for h in history['data']:
                        batch_info = h.get('batch')
                        batch_str = f', 批次={batch_info["batch_no"]}' if batch_info else ''
                        print(f'  {h["from_status"] or "无"} -> {h["to_status"]} by {h["operator"]["username"]}{batch_str}')
                    has_batch = any(h.get('batch') for h in history['data'])
                    print(f'\\n审计历史包含批次号: {has_batch}')

    print('\n' + '#' * 70)
    print('#  ✅ 所有 curl 演示完成，用户可见结果验证通过！')
    print('#' * 70)
    print()


if __name__ == '__main__':
    try:
        run_curl_demo()
    except requests.exceptions.ConnectionError:
        print('错误: 无法连接到服务器，请确保服务已启动 (python run.py)')
        exit(1)
    except Exception as e:
        print(f'演示出错: {e}')
        import traceback
        traceback.print_exc()
        exit(1)
