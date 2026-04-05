from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app


@pytest_asyncio.fixture
async def student_api_session(tmp_path: Path):
    db_path = tmp_path / "student_profile_api.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_student_profile_build_and_batch_api(student_api_session):
    async def override_db():
        yield student_api_session

    app.dependency_overrides[get_db_session] = override_db
    transport = ASGITransport(app=app)

    build_payload = {
        "source": {
            "student_id": "api-001",
            "resume_text": "学校: 武汉大学。专业: 计算机科学与技术。本科。项目经历: 校园服务平台。",
            "manual_form": {"skills": ["Python", "SQL"], "certificates": ["CET-6"]},
            "supplement_text": "求职意向: 数据开发工程师。",
            "basic_info": {"student_name": "李四"}
        },
        "persist": False
    }
    batch_payload = {
        "items": [
            {
                "student_id": "api-002",
                "resume_text": "学校: 中山大学。专业: 金融学。本科。",
                "manual_form": {"skills": ["Excel"]},
                "supplement_text": "",
                "basic_info": {}
            },
            {
                "student_id": "api-003",
                "resume_text": "学校: 西安交通大学。专业: 电气工程。本科。",
                "manual_form": {"skills": ["Python"]},
                "supplement_text": "",
                "basic_info": {}
            }
        ],
        "persist": False
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        build_response = await client.post("/api/v1/student-profiles/build", json=build_payload)
        batch_response = await client.post("/api/v1/student-profiles/batch", json=batch_payload)

    app.dependency_overrides.clear()

    assert build_response.status_code == 200
    build_body = build_response.json()
    assert build_body["student_id"] == "api-001"
    assert build_body["profile"]["school"] == "武汉大学"
    assert "Python" in build_body["profile"]["skills"]
    assert isinstance(build_body["profile"]["summary"], str)
    assert isinstance(build_body["profile"]["evidence"], dict)
    assert all(isinstance(value, list) for value in build_body["profile"]["evidence"].values())

    assert batch_response.status_code == 200
    batch_body = batch_response.json()
    assert batch_body["processed_records"] == 2
    assert batch_body["failed_records"] == 0


@pytest.mark.asyncio
async def test_student_profile_get_update_and_rebuild_api(student_api_session):
    async def override_db():
        yield student_api_session

    app.dependency_overrides[get_db_session] = override_db
    transport = ASGITransport(app=app)
    build_payload = {
        "source": {
            "student_id": "api-010",
            "resume_text": "学校: 南京大学。专业: 软件工程。本科。项目经历: 选课系统。",
            "manual_form": {"skills": ["Java"]},
            "supplement_text": "求职意向: Java 开发工程师。",
            "basic_info": {}
        },
        "persist": True
    }
    update_payload = {
        "manual_form": {"skills": ["Java", "Spring Boot"], "projects": ["选课系统"]},
        "persist": True
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        build_response = await client.post("/api/v1/student-profiles/build", json=build_payload)
        get_response = await client.get("/api/v1/student-profiles/api-010")
        update_response = await client.patch("/api/v1/student-profiles/api-010", json=update_payload)
        rebuild_response = await client.post("/api/v1/student-profiles/api-010/rebuild")

    app.dependency_overrides.clear()

    assert build_response.status_code == 200
    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert rebuild_response.status_code == 200

    assert get_response.json()["profile_version"] == 1
    assert update_response.json()["profile_version"] == 2
    assert rebuild_response.json()["profile_version"] == 3
    assert "Spring Boot" in update_response.json()["profile"]["skills"]
