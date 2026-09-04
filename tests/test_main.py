import importlib

import pytest

import app.main as main_module
from app.models.appearance import AppearanceSettings
from app.models.feature import FeatureFlag, DEFAULT_FEATURES


def test_seed_default_features_when_features_already_exist(db_session, monkeypatch):
    monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)

    for key, display_name in DEFAULT_FEATURES:
        db_session.add(
            FeatureFlag(
                key=key,
                display_name=display_name,
                is_enabled=True,
            )
        )
    db_session.commit()

    main_module.seed_default_features()

    features = db_session.query(FeatureFlag).all()

    assert len(features) == len(DEFAULT_FEATURES)
    assert {
        feature.key for feature in features
    } == {key for key, _ in DEFAULT_FEATURES}


def test_seed_default_appearance_when_appearance_already_exists(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)

    existing = AppearanceSettings()
    db_session.add(existing)
    db_session.commit()

    main_module.seed_default_appearance()

    appearances = db_session.query(AppearanceSettings).all()

    assert len(appearances) == 1


@pytest.mark.asyncio
async def test_lifespan_scheduler_enabled_success(
    monkeypatch,
):
    create_all_called = False
    init_called = False
    shutdown_called = False

    def fake_create_all(*args, **kwargs):
        nonlocal create_all_called
        create_all_called = True

    def fake_init_scheduler():
        nonlocal init_called
        init_called = True

    def fake_shutdown_scheduler():
        nonlocal shutdown_called
        shutdown_called = True

    monkeypatch.setattr(main_module.Base.metadata, "create_all", fake_create_all)
    monkeypatch.setattr(main_module, "seed_default_features", lambda: None)
    monkeypatch.setattr(main_module, "seed_default_appearance", lambda: None)
    monkeypatch.setattr(main_module, "init_scheduler", fake_init_scheduler)
    monkeypatch.setattr(main_module, "shutdown_scheduler", fake_shutdown_scheduler)
    monkeypatch.setattr(
        main_module.settings,
        "SCHEDULER_ENABLED",
        True,
    )

    async with main_module.lifespan(main_module.app):
        assert create_all_called is True
        assert init_called is True
        assert shutdown_called is False

    assert shutdown_called is True


@pytest.mark.asyncio
async def test_lifespan_scheduler_start_failure(
    monkeypatch,
):
    shutdown_called = False

    def fake_init_scheduler():
        raise RuntimeError("scheduler startup failed")

    def fake_shutdown_scheduler():
        nonlocal shutdown_called
        shutdown_called = True

    monkeypatch.setattr(main_module.Base.metadata, "create_all", lambda *a, **k: None)
    monkeypatch.setattr(main_module, "seed_default_features", lambda: None)
    monkeypatch.setattr(main_module, "seed_default_appearance", lambda: None)
    monkeypatch.setattr(main_module, "init_scheduler", fake_init_scheduler)
    monkeypatch.setattr(main_module, "shutdown_scheduler", fake_shutdown_scheduler)
    monkeypatch.setattr(
        main_module.settings,
        "SCHEDULER_ENABLED",
        True,
    )

    async with main_module.lifespan(main_module.app):
        pass

    assert shutdown_called is True


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"]


def test_main_storage_setup_oserror(monkeypatch):
    original_makedirs = main_module.os.makedirs

    def raise_os_error(*args, **kwargs):
        raise OSError("test storage error")

    monkeypatch.setattr(main_module.os, "makedirs", raise_os_error)

    try:
        reloaded = importlib.reload(main_module)

        assert reloaded.app is not None

        storage_routes = [
            route
            for route in reloaded.app.routes
            if getattr(route, "path", None) == "/storage"
        ]

        assert storage_routes == []
    finally:
        monkeypatch.setattr(main_module.os, "makedirs", original_makedirs)
        importlib.reload(main_module)
