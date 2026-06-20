from app.schemas import BackendPoolCreate, BackendServerBase, LoadBalancingMethod
from app.services.backend_pool_service import BackendPoolService


def test_create_pool(db_session, temp_settings):
    service = BackendPoolService(temp_settings, db_session)
    pool = service.create_pool(
        BackendPoolCreate(
            name="app-pool",
            proxy_id="myapp",
            load_balancing_method=LoadBalancingMethod.WEIGHTED,
            servers=[
                BackendServerBase(name="s1", host="192.168.1.10", port=443, protocol="https", weight=10),
                BackendServerBase(name="s2", host="192.168.1.11", port=443, protocol="https", weight=5, role="backup"),
            ],
        )
    )
    assert pool.name == "app-pool"
    assert len(pool.servers) == 2
    assert pool.backup_count == 1


def test_list_load_balancers(db_session, temp_settings):
    service = BackendPoolService(temp_settings, db_session)
    service.create_pool(
        BackendPoolCreate(
            name="lb1",
            load_balancing_method=LoadBalancingMethod.ROUND_ROBIN,
            servers=[BackendServerBase(name="s1", host="10.0.0.1", port=80)],
        )
    )
    summaries = service.list_load_balancers()
    assert len(summaries) == 1
    assert summaries[0].pool_name == "lb1"
