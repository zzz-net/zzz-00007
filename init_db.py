from app import storage
from app.models import Role, System, User


def init_database():
    roles_data = [
        ('APPLICANT', '申请人：提交变更冻结例外申请，可撤回自己的申请'),
        ('REVIEWER', '风险复核人：对申请进行风险评估和复核'),
        ('APPROVER', '审批人：对已复核通过的申请进行审批，可生效或再次批准撤回的申请')
    ]

    for name, description in roles_data:
        if not storage.get_role_by_name(name):
            storage.create_role(name, description)

    systems_data = [
        ('PAYMENT-SYSTEM', '核心支付系统，处理在线支付交易'),
        ('USER-SERVICE', '用户中心服务，管理用户账号和信息'),
        ('ORDER-SYSTEM', '订单系统，处理订单创建和流转'),
        ('INVENTORY-SYSTEM', '库存系统，管理商品库存信息')
    ]

    for name, description in systems_data:
        if not storage.get_system_by_name(name):
            storage.create_system(name, description)

    applicant_role = storage.get_role_by_name('APPLICANT')
    reviewer_role = storage.get_role_by_name('REVIEWER')
    approver_role = storage.get_role_by_name('APPROVER')

    users_data = [
        ('zhangsan', applicant_role.id),
        ('lisi', applicant_role.id),
        ('wangwu', reviewer_role.id),
        ('zhaoliu', reviewer_role.id),
        ('qianqi', approver_role.id),
        ('sunba', approver_role.id)
    ]

    for username, role_id in users_data:
        if not storage.get_user_by_username(username):
            storage.create_user(username, role_id)

    print('数据库初始化完成！')
    print('已创建角色:')
    for role in storage.get_all_roles():
        print(f'  - {role.name}: {role.description}')
    print('\n已创建系统:')
    for system in storage.get_all_systems():
        print(f'  - {system.name}: {system.description}')
    print('\n已创建用户:')
    for user in User.query.all():
        print(f'  - {user.username} (角色: {user.role.name})')
