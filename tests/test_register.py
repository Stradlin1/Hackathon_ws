from state.register import validate_registration


def test_registration_accepts_chinese_name():
    name, username, email, error = validate_registration(
        '张三', 'zhang@example.com', 'ZhangSan', 'demo1234', 'demo1234', {}
    )
    assert error is None
    assert name == '张三'
    assert username == 'zhangsan'
    assert email == 'zhang@example.com'


def test_registration_rejects_weak_password():
    _, _, _, error = validate_registration('张三', 'zhang@example.com', 'zhangsan', '12345678', '12345678', {})
    assert error == '密码需要同时包含字母和数字。'
    _, _, _, error = validate_registration('张三', 'zhang@example.com', 'zhangsan', 'demo123', 'demo123', {})
    assert error == '密码至少 8 位。'


def test_registration_rejects_duplicate_username_and_email():
    existing = {'alice': {'email': 'alice@example.com'}}
    _, _, _, error = validate_registration('张三', 'zhang@example.com', 'Alice', 'demo1234', 'demo1234', existing)
    assert error == '这个用户名已经被注册。'
    _, _, _, error = validate_registration('张三', 'ALICE@example.com', 'zhangsan', 'demo1234', 'demo1234', existing)
    assert error == '这个邮箱已经被使用。'


def test_registration_rejects_chinese_username_and_mismatch():
    _, _, _, error = validate_registration('张三', 'zhang@example.com', '张三', 'demo1234', 'demo1234', {})
    assert '用户名需为' in error
    _, _, _, error = validate_registration('张三', 'zhang@example.com', 'zhangsan', 'demo1234', 'demo12345', {})
    assert error == '两次输入的密码不一致。'
