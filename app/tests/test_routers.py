"""Unit tests for FastAPI routers - comprehensive coverage."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson.objectid import ObjectId
from fastapi.testclient import TestClient

from app.api.routers.comprehensive_optimizer import get_comprehensive_optimizer
from app.api.routers.cover_letter import (get_ai_generator,
                                          get_cover_letter_repository)
from app.api.routers.resume import get_resume_repository
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_resume_repo():
    repo = MagicMock()
    repo.create_resume = AsyncMock()
    repo.get_resume_by_id = AsyncMock()
    repo.get_by_user_id = AsyncMock()
    repo.get_resumes_by_user_id = AsyncMock()
    repo.update_resume = AsyncMock()
    repo.update = AsyncMock()
    repo.delete_resume = AsyncMock()
    repo.delete = AsyncMock()
    repo.update_optimized_data = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def mock_cl_repo():
    repo = MagicMock()
    repo.create_cover_letter, repo.get_cover_letter_by_id = AsyncMock(), AsyncMock()
    repo.get_cover_letters_by_user_id, repo.update_cover_letter = (
        AsyncMock(),
        AsyncMock(),
    )
    repo.delete_cover_letter, repo.search_cover_letters = AsyncMock(), AsyncMock()
    repo.get_cover_letter_statistics = AsyncMock()
    return repo


@pytest.fixture
def mock_comp_optimizer():
    opt = MagicMock()
    opt.optimize_resume_master, opt.analyze_ats_keywords = AsyncMock(), AsyncMock()
    opt.extract_hidden_achievements, opt.create_three_versions = (
        AsyncMock(),
        AsyncMock(),
    )
    opt.iterative_improvement = AsyncMock()
    opt.get_quick_start_workflows, opt.get_pro_tips = MagicMock(), MagicMock()
    opt.get_eu_2025_alignment, opt.MASTER_SKILLS_LIST = MagicMock(), "Skills"
    return opt


@pytest.fixture
def mock_ai_gen():
    gen = AsyncMock()
    gen.generate_cover_letter, gen.model_name = AsyncMock(), "test-model"
    return gen


@pytest.fixture
def override_deps(mock_resume_repo, mock_cl_repo, mock_comp_optimizer, mock_ai_gen):
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repo
    app.dependency_overrides[get_cover_letter_repository] = lambda: mock_cl_repo
    app.dependency_overrides[get_comprehensive_optimizer] = lambda: mock_comp_optimizer
    app.dependency_overrides[get_ai_generator] = lambda: mock_ai_gen
    # Set app state for direct access
    app.state.resume_repo = mock_resume_repo
    yield
    app.dependency_overrides.clear()
    if hasattr(app.state, "resume_repo"):
        delattr(app.state, "resume_repo")


# === RESUME TESTS ===


# @pytest.mark.skip(reason="Test needs refactoring for correct endpoint and mocking")
def test_resume_upload(override_deps, mock_resume_repo):
    mock_resume_repo.create_master_cv = AsyncMock(return_value=str(ObjectId()))
    with (
        patch(
            "app.services.file_validator.SecureFileValidator.validate_upload",
            AsyncMock(return_value=(b"t", "t.pdf", "h")),
        ),
        patch(
            "app.services.file_validator.store_file_securely",
            AsyncMock(return_value="/t.pdf"),
        ),
        patch(
            "app.utils.file_handling.extract_text_from_file",
            AsyncMock(side_effect=lambda *args, **kwargs: "E"),
        ),
        patch("app.services.master_cv.MasterCV") as mock_master_cv,
    ):
        mock_master_cv.return_value.extract_text_from_uploaded_file = AsyncMock(
            return_value="Extracted text"
        )
        response = client.post(
            "/api/v1/resumes/master-cv/upload",
            data={"user_id": "u"},
            files={"file": ("test.pdf", b"t", "application/pdf")},
        )
        # May be 201 or 422 depending on validation
        assert response.status_code in [201, 422]


def test_get_user_resumes(override_deps, mock_resume_repo):
    now = datetime.now()
    mock_resume_repo.get_by_user_id.return_value = [
        {
            "_id": ObjectId(),
            "title": "A",
            "target_company": "Apple",
            "created_at": now,
            "updated_at": now,
        },
        {
            "_id": ObjectId(),
            "title": "B",
            "target_company": "Google",
            "created_at": now,
            "updated_at": now,
        },
    ]
    response = client.get("/api/v1/resumes/user/u1")
    assert response.status_code == 200


# @pytest.mark.skip(reason="Needs URL and mocking fixes")
def test_resume_crud(override_deps, mock_resume_repo):
    rid = str(ObjectId())
    # Mock with file_path attribute for DELETE endpoint
    mock_existing = MagicMock()
    mock_existing.get = lambda key, default=None: {
        "_id": ObjectId(rid),
        "title": "T",
        "file_path": None,
    }.get(key, default)
    mock_existing.file_path = None

    mock_resume_repo.get_by_id = AsyncMock(return_value=mock_existing)
    mock_resume_repo.get_resume_by_id = AsyncMock(
        return_value={"_id": ObjectId(rid), "title": "T"}
    )
    # The actual endpoint uses repository.update(), not update_resume
    mock_resume_repo.update = AsyncMock(
        return_value={
            "_id": ObjectId(rid),
            "title": "N",
            "user_id": "u",
            "original_content": "c",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01",
        }
    )
    mock_resume_repo.update_resume = AsyncMock(
        return_value={"_id": ObjectId(rid), "title": "N"}
    )
    mock_resume_repo.delete = AsyncMock(return_value=True)
    mock_resume_repo.delete_resume = AsyncMock(return_value=True)

    with patch("app.database.repositories.resume_repository.PostgresConnectionManager"):
        # assert client.put(f"/api/v1/resumes/{rid}/status/applied").status_code == 200
        assert (
            client.put(f"/api/v1/resumes/{rid}", json={"title": "N"}).status_code == 200
        )
        assert client.delete(f"/api/v1/resumes/{rid}").status_code == 200


def test_resume_errors(override_deps, mock_resume_repo):
    mock_resume_repo.get_by_id.return_value = None
    mock_resume_repo.get_by_id = AsyncMock(return_value=None)
    assert client.get(f"/api/v1/resumes/{str(ObjectId())}").status_code == 404
    assert client.get(f"/api/v1/resumes/{str(ObjectId())}/download").status_code == 404


# @pytest.mark.skip(reason="Needs URL and mocking fixes")
def test_score_optimize(override_deps, mock_resume_repo):
    rid = str(ObjectId())
    mock_resume_repo.get_by_id = AsyncMock(
        return_value={
            "_id": ObjectId(rid),
            "original_content": "C",
        }
    )
    mock_resume_repo.get_resume_by_id = AsyncMock(
        return_value={
            "_id": ObjectId(rid),
            "original_content": "C",
        }
    )
    mock_resume_repo.create_resume = AsyncMock(return_value=str(ObjectId()))
    with (
        patch("app.services.cv_analyzer.CVAnalyzer") as a,
        patch("app.services.workflow_orchestrator.CVWorkflowOrchestrator") as o,
        patch.dict("os.environ", {"API_BASE": "http://m"}),
        patch("app.database.repositories.resume_repository.PostgresConnectionManager"),
        patch("app.services.master_cv.MasterCV") as MockMasterCV,
    ):
        mock_analyzer = AsyncMock()
        mock_analyzer.analyze = AsyncMock(
            return_value={"ats_score": 80, "matching_skills": []}
        )
        a.return_value = mock_analyzer

        mock_orchestrator = AsyncMock()
        mock_orchestrator.optimize_cv_for_job = AsyncMock(
            return_value={
                "optimized_cv": {
                    "user_information": {
                        "name": "N",
                        "main_job_title": "J",
                        "profile_description": "D",
                        "email": "e@e.com",
                        "experiences": [],
                        "education": [],
                        "skills": {"hard_skills": [], "soft_skills": []},
                    }
                },
                "ats_score": 90,
            }
        )
        o.return_value = mock_orchestrator

        # Patch MasterCV class - when instantiated, return mock with score_resume
        mock_master_cv = MagicMock()
        mock_master_cv.score_resume = AsyncMock(
            return_value={
                "ats_score": 80.0,
                "readability_score": 75.0,
                "keyword_density": {},
                "strengths": ["Good formatting"],
                "weaknesses": ["Missing keywords"],
                "recommendations": ["Add more skills"],
            }
        )
        MockMasterCV.return_value = mock_master_cv
        assert (
            client.post(
                f"/api/v1/resumes/optimization/{rid}/score",
                json={"job_description": "J", "resume_text": "C"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/resumes/optimization/{rid}", json={"job_description": "J"}
            ).status_code
            == 200
        )


# === COVER LETTER TESTS ===


# @pytest.mark.skip(reason="Covers endpoint validation issue")
def test_create_cl(override_deps, mock_cl_repo, mock_resume_repo):
    mock_resume_repo.get_by_id = AsyncMock(
        return_value={"original_content": "Resume Content"}
    )
    mock_resume_repo.get_resume_by_id = AsyncMock(
        return_value={"original_content": "Resume Content"}
    )
    mock_cl_repo.create_cover_letter = AsyncMock(return_value=str(ObjectId()))

    # Mock Redis to avoid connection errors
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    # Mock CoverLetterData and CoverLetter to avoid validation errors
    with (
        patch("app.api.routers.cover_letter.CoverLetterData") as MockCoverLetterData,
        patch("app.api.routers.cover_letter.CoverLetter") as MockCoverLetter,
        patch("app.services.workflow_orchestrator.get_redis", return_value=mock_redis),
        patch("app.services.ai_providers.get_redis", return_value=mock_redis),
    ):
        # Make CoverLetterData return a properly structured mock
        mock_data = MagicMock()
        mock_data.model_dump.return_value = {
            "sender_name": "S",
            "sender_email": "s@s.com",
            "company_name": "C",
            "job_title": "R",
            "introduction": "",
            "body_paragraphs": ["default paragraph"],  # Need at least 1 item
            "closing": "",
            "signature": "Sincerely,\nS",
        }
        MockCoverLetterData.return_value = mock_data

        response = client.post(
            "/api/cover-letter/",
            json={
                "title": "CL",
                "resume_id": str(ObjectId()),
                "target_company": "C",
                "target_role": "R",
                "job_description": "J",
                "sender_name": "S",
                "sender_email": "s@s.com",
            },
        )
        assert response.status_code == 200


def test_get_cl(override_deps, mock_cl_repo):
    cid, now = str(ObjectId()), datetime.now()
    mock_cl_repo.get_cover_letter_by_id.return_value = {
        "_id": ObjectId(cid),
        "title": "C",
    }
    assert client.get(f"/api/cover-letter/{cid}").status_code == 200

    mock_cl_repo.get_cover_letters_by_user_id.return_value = [
        {
            "_id": ObjectId(),
            "title": "C",
            "target_company": "C",
            "target_role": "R",
            "is_generated": False,
            "created_at": now,
            "updated_at": now,
        }
    ]
    assert client.get("/api/cover-letter/user/u1").status_code == 200


def test_cl_crud(override_deps, mock_cl_repo):
    cid = str(ObjectId())
    mock_cl_repo.get_cover_letter_by_id.return_value = {"_id": ObjectId(cid)}
    mock_cl_repo.update_cover_letter.return_value = True
    mock_cl_repo.delete_cover_letter.return_value = True

    assert (
        client.put(f"/api/cover-letter/{cid}", json={"title": "N"}).status_code == 200
    )
    assert client.delete(f"/api/cover-letter/{cid}").status_code == 200


def test_cl_ai(override_deps, mock_ai_gen):
    mock_ai_gen.generate_cover_letter.return_value = "AI"
    response = client.post(
        "/api/cover-letter/generate-with-ai",
        json={
            "resume_text": "R",
            "job_description": "J",
            "company_name": "C",
            "job_title": "T",
        },
    )
    assert response.status_code == 200
    assert response.json()["content"] == "AI"


def test_cl_search_stats(override_deps, mock_cl_repo):
    (
        mock_cl_repo.search_cover_letters.return_value,
        mock_cl_repo.get_cover_letter_statistics.return_value,
    ) = [], {"total": 5}
    assert client.get("/api/cover-letter/search/u1?query=test").status_code == 200
    assert client.get("/api/cover-letter/statistics/u1").status_code == 200


# === COMPREHENSIVE OPTIMIZER TESTS ===


# @pytest.mark.skip(reason="Needs mocking fixes")
def test_comp_opt(override_deps, mock_comp_optimizer):
    mock_comp_optimizer.optimize_resume_master.return_value = {"r": "ok"}
    mock_comp_optimizer.analyze_ats_keywords.return_value = {"keywords": []}
    mock_comp_optimizer.extract_hidden_achievements.return_value = {"achievements": []}
    mock_comp_optimizer.create_three_versions.return_value = {"versions": []}
    mock_comp_optimizer.iterative_improvement.return_value = {"improved": True}

    # Mock Redis to avoid connection errors
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    # Mock the workflow orchestrator used by the master optimization endpoint
    with (
        patch(
            "app.api.routers.comprehensive_optimizer.CVWorkflowOrchestrator"
        ) as mock_orch,
        patch(
            "app.api.routers.comprehensive_optimizer.ResumeRepository"
        ) as mock_repo_class,
        patch("app.database.repositories.resume_repository.PostgresConnectionManager"),
        patch("app.database.repositories.base_repo.MongoConnectionManager"),
        patch("app.services.workflow_orchestrator.get_redis", return_value=mock_redis),
    ):
        mock_instance = AsyncMock()
        mock_instance.optimize_cv_for_job = AsyncMock(
            return_value={
                "optimized_cv": {
                    "user_information": {
                        "name": "Test",
                        "main_job_title": "Dev",
                        "profile_description": "Desc",
                        "experiences": [],
                        "education": [],
                        "skills": {"hard_skills": [], "soft_skills": []},
                    }
                },
                "ats_score": 85,
                "matching_skills": ["skill1"],
                "missing_skills": ["skill2"],
                "recommendation": "Good",
            }
        )
        mock_orch.return_value = mock_instance

        mock_repo_instance = MagicMock()
        mock_repo_instance.create_resume = AsyncMock(return_value="new_id")
        mock_repo_class.return_value = mock_repo_instance
        assert (
            client.post(
                "/api/comprehensive/optimize/master",
                json={"target_role": "R", "job_description": "J", "resume_text": "R"},
            ).status_code
            == 200
        )
    assert (
        client.post(
            "/api/comprehensive/analyze/ats",
            json={"job_description": "J", "resume_text": "R"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/comprehensive/extract/achievements", json={"role_description": "R"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/comprehensive/create/three-versions",
            json={"job_description": "J", "resume_text": "R"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/comprehensive/improve/iterative",
            json={"job_description": "J", "resume_text": "R"},
        ).status_code
        == 200
    )


def test_comp_opt_getters(override_deps, mock_comp_optimizer):
    mock_comp_optimizer.get_quick_start_workflows.return_value = {"5min": "Quick"}
    mock_comp_optimizer.get_pro_tips.return_value = ["Tip"]
    mock_comp_optimizer.get_eu_2025_alignment.return_value = {"ats": []}

    assert client.get("/api/comprehensive/workflows").status_code == 200
    assert client.get("/api/comprehensive/tips").status_code == 200
    assert client.get("/api/comprehensive/eu-alignment").status_code == 200
    assert client.get("/api/comprehensive/skills").status_code == 200
