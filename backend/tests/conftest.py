"""
pytest 全局配置和共享夹具
- 使用 SQLite 内存数据库进行测试，不影响 PostgreSQL
- 提供 TestClient、数据库会话、测试用户等夹具
"""
import os

# 测试环境变量（必须在 import app 模块之前设置，否则 Settings 单例会用空值初始化）
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-only-32chars!!")
os.environ.setdefault("DEBUG", "True")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.session import Base, get_db
from app.entity.db_models import User
from app.core.security import hash_password
from app.config.settings import settings

# 创建 SQLite 内存数据库引擎（测试专用，不连接 PostgreSQL）
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """在所有测试前创建数据库表，在所有测试后删除"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """
    提供独立的数据库会话，每次测试后回滚。
    采用"连接级 SAVEPOINT"方案：
    1. 先开启一个 connection 级的外层事务（不提交，最后回滚）
    2. 在该连接上创建一个 session，并在 connection 上开启 SAVEPOINT
    3. 测试代码中的 db.commit() 会提交并关闭当前 SAVEPOINT；通过事件监听自动重新开启
    4. 测试结束回滚外层 connection 事务，所有数据自动清理
    这种方式对 SQLite 更可靠，能彻底避免跨测试数据污染。
    """
    from sqlalchemy import event

    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)
    savepoint = connection.begin_nested()

    # 当 SAVEPOINT 被提交（db.commit()）后自动重新开启，保证后续 commit 仍被包裹
    @event.listens_for(db, "after_transaction_end")
    def restart_savepoint(session, current_transaction):
        nonlocal savepoint
        if not savepoint.is_active:
            savepoint = connection.begin_nested()

    try:
        yield db
    finally:
        # 移除事件监听，避免 fixture 间互相干扰
        event.remove(db, "after_transaction_end", restart_savepoint)
        db.close()
        transaction.rollback()  # 回滚外层事务，清理所有测试数据
        connection.close()


@pytest.fixture
def client(db_session, monkeypatch):
    """
    提供 FastAPI TestClient
    使用 SQLite 测试数据库替代 PostgreSQL
    """
    import main as main_module
    from app.middleware.audit_log import AuditLogMiddleware

    app = main_module.app

    # 覆盖 get_db 依赖，使用测试数据库
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        "test-only-jwt-secret-key-"
        "0123456789abcdef0123456789abcdef",
    )
    monkeypatch.setattr(main_module, "init_minio", lambda: None)
    # API tests isolate persistence here; test_audit_log.py exercises the real
    # method directly without requesting this fixture.
    monkeypatch.setattr(
        AuditLogMiddleware,
        "_save_log",
        lambda self, **kwargs: None,
    )
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "Test123456",
    }


@pytest.fixture
def create_test_user(db_session, test_user_data):
    """在数据库中创建测试用户，返回 User 对象"""
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        hashed_password=hash_password(test_user_data["password"]),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
