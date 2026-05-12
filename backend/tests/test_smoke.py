"""冒烟测试 — 验证 app 能正常启动，基础路由可访问

只做最轻量的检查，不做重依赖或真实 IO。
"""

def test_app_starts(client):
    """app 能正常实例化，不抛异常"""
    # FastAPI 的 TestClient 在构造时就会失败，所以能走到这里说明 app 没问题
    assert client is not None


def test_root_responds(client):
    """根路径已注册路由，应返回 200"""
    resp = client.get("/")
    assert resp.status_code == 200


def test_nonexistent_path_404(client):
    """不存在的路径应返回 404（而非 500）"""
    resp = client.get("/nonexistent_path_abc123")
    assert resp.status_code == 404


def test_api_prefix_no_crash(client):
    """所有 /api/... 路由注册不产生异常"""
    # 用一个不存在的子路径探测，确认路由表已加载
    resp = client.get("/api/nonexistent_path_12345")
    # 允许 401/403/404，但不允许 500
    assert resp.status_code != 500
