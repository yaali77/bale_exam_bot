from datetime import date
import uuid

from app.models.admin import AdminRole
from app.models.exam import Exam
from app.models.result import Result, ResultStatus, ResultHistory
from app.models.user import User


def _create_user_and_exam(db_session):
    user = User(
        bale_user_id=100000001,
        phone_number="09121111111",
        national_code="1111111111",
        first_name="Test",
        last_name="User",
    )

    exam = Exam(
        title="Results Test Exam",
        exam_code=f"RESULT-{uuid.uuid4().hex[:8]}",
        exam_date=date(2026, 9, 3),
        total_score=100,
        passing_score=60,
    )

    db_session.add_all([user, exam])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(exam)

    return user, exam


def _create_result(db_session, user, exam, score=75):
    result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=score,
        is_passed=score >= exam.passing_score,
        status=ResultStatus.RECORDED,
    )

    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)

    return result


def test_create_result_success(client, db_session, super_admin_token):
    user, exam = _create_user_and_exam(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        "/api/results",
        json={
            "user_national_code": user.national_code,
            "exam_id": str(exam.id),
            "score": "85",
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == str(user.id)
    assert data["exam_id"] == str(exam.id)
    assert float(data["score"]) == 85
    assert data["is_passed"] is True
    assert data["status"] == ResultStatus.RECORDED.value


def test_create_result_calculates_failed_status(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        "/api/results",
        json={
            "user_national_code": user.national_code,
            "exam_id": str(exam.id),
            "score": "45",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["is_passed"] is False


def test_create_result_rejects_score_above_total(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        "/api/results",
        json={
            "user_national_code": user.national_code,
            "exam_id": str(exam.id),
            "score": "101",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert db_session.query(Result).count() == 0


def test_create_result_rejects_negative_score(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        "/api/results",
        json={
            "user_national_code": user.national_code,
            "exam_id": str(exam.id),
            "score": "-1",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert db_session.query(Result).count() == 0


def test_create_result_rejects_duplicate_result(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    existing_result = Result(
        user_id=user.id,
        exam_id=exam.id,
        score=70,
        is_passed=True,
        status=ResultStatus.RECORDED,
    )

    db_session.add(existing_result)
    db_session.commit()

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        "/api/results",
        json={
            "user_national_code": user.national_code,
            "exam_id": str(exam.id),
            "score": "80",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert db_session.query(Result).count() == 1


def test_create_result_requires_existing_user(
    client,
    db_session,
    super_admin_token,
):
    _, exam = _create_user_and_exam(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        "/api/results",
        json={
            "user_national_code": "9999999999",
            "exam_id": str(exam.id),
            "score": "80",
        },
        headers=headers,
    )

    assert response.status_code == 404


def test_create_result_requires_existing_exam(
    client,
    db_session,
    super_admin_token,
):
    user, _ = _create_user_and_exam(db_session)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        "/api/results",
        json={
            "user_national_code": user.national_code,
            "exam_id": str(uuid.uuid4()),
            "score": "80",
        },
        headers=headers,
    )

    assert response.status_code == 404


def test_update_result_score_success(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=75)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "score": "85",
            "change_reason": "اصلاح نمره",
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert float(data["score"]) == 85
    assert data["is_passed"] is True
    assert data["status"] == ResultStatus.RECORDED.value

    db_session.refresh(result)

    assert result.score == 85
    assert result.is_passed is True


def test_update_result_recalculates_failed_status(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=75)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "score": "40",
            "change_reason": "اصلاح نمره",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert float(response.json()["score"]) == 40
    assert response.json()["is_passed"] is False

    db_session.refresh(result)

    assert result.score == 40
    assert result.is_passed is False


def test_update_result_rejects_score_above_total(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=75)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "score": "101",
            "change_reason": "نمره نامعتبر",
        },
        headers=headers,
    )

    assert response.status_code == 400

    db_session.refresh(result)

    assert result.score == 75


def test_update_result_rejects_negative_score(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=75)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "score": "-1",
            "change_reason": "نمره نامعتبر",
        },
        headers=headers,
    )

    assert response.status_code == 400

    db_session.refresh(result)

    assert result.score == 75


def test_update_result_creates_history(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=75)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "score": "85",
            "change_reason": "اصلاح نمره",
        },
        headers=headers,
    )

    assert response.status_code == 200

    history = (
        db_session.query(ResultHistory)
        .filter(ResultHistory.result_id == result.id)
        .order_by(ResultHistory.changed_at.desc())
        .first()
    )

    assert history is not None
    assert history.previous_score == 75
    assert history.new_score == 85
    assert history.previous_status == ResultStatus.RECORDED.value
    assert history.new_status == ResultStatus.RECORDED.value
    assert history.reason == "اصلاح نمره"


def test_update_result_history_records_admin(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=75)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "score": "85",
            "change_reason": "اصلاح نمره",
        },
        headers=headers,
    )

    assert response.status_code == 200

    history = (
        db_session.query(ResultHistory)
        .filter(ResultHistory.result_id == result.id)
        .first()
    )

    assert history is not None
    assert history.changed_by_admin_id is not None


def test_update_result_not_found(
    client,
    db_session,
    super_admin_token,
):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        f"/api/results/{uuid.uuid4()}",
        json={
            "score": "85",
            "change_reason": "تست",
        },
        headers=headers,
    )

    assert response.status_code == 404

def test_publish_result_success(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=80)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/results/{result.id}/publish",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == ResultStatus.PUBLISHED.value
    assert data["published_at"] is not None

    db_session.refresh(result)

    assert result.status == ResultStatus.PUBLISHED
    assert result.published_at is not None
    assert result.published_by_admin_id is not None


def test_publish_result_not_found(
    client,
    db_session,
    super_admin_token,
):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/results/{uuid.uuid4()}/publish",
        headers=headers,
    )

    assert response.status_code == 404


def test_publish_result_creates_history(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=80)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/results/{result.id}/publish",
        headers=headers,
    )

    assert response.status_code == 200

    history = (
        db_session.query(ResultHistory)
        .filter(ResultHistory.result_id == result.id)
        .order_by(ResultHistory.changed_at.desc())
        .first()
    )

    assert history is not None
    assert history.previous_status == ResultStatus.RECORDED.value
    assert history.new_status == ResultStatus.PUBLISHED.value
    assert history.changed_by_admin_id is not None
def test_unpublish_result_creates_history(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=80)

    result.status = ResultStatus.PUBLISHED
    result.published_at = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    )
    db_session.commit()
    db_session.refresh(result)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/results/{result.id}/unpublish",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == ResultStatus.REVIEWED.value
    assert data["published_at"] is None

    db_session.refresh(result)

    assert result.status == ResultStatus.REVIEWED
    assert result.published_at is None

    history = (
        db_session.query(ResultHistory)
        .filter(ResultHistory.result_id == result.id)
        .order_by(ResultHistory.changed_at.desc())
        .first()
    )

    assert history is not None
    assert history.previous_status == ResultStatus.PUBLISHED.value
    assert history.new_status == ResultStatus.REVIEWED.value
    assert history.changed_by_admin_id == db_session.query(
        ResultHistory.changed_by_admin_id
    ).filter(
        ResultHistory.result_id == result.id
    ).scalar()

def test_void_result_success(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=80)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/results/{result.id}/void",
        params={"reason": "????? ?? ???? ??? ??????"},
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == ResultStatus.VOIDED.value

    db_session.refresh(result)

    assert result.status == ResultStatus.VOIDED
    assert result.change_reason == "????? ?? ???? ??? ??????"


def test_void_result_creates_history(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=80)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/results/{result.id}/void",
        params={"reason": "????? ?????"},
        headers=headers,
    )

    assert response.status_code == 200

    history = (
        db_session.query(ResultHistory)
        .filter(ResultHistory.result_id == result.id)
        .order_by(ResultHistory.changed_at.desc())
        .first()
    )

    assert history is not None
    assert history.previous_score == 80
    assert history.new_score == 80
    assert history.previous_status == ResultStatus.RECORDED.value
    assert history.new_status == ResultStatus.VOIDED.value
    assert history.reason == "????? ?????"

    from app.models.admin import Admin

    admin = db_session.query(Admin).filter(
        Admin.username == "admin_test"
    ).first()

    assert history.changed_by_admin_id == admin.id


def test_void_result_clears_publication_data(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(db_session, user, exam, score=90)

    from app.models.admin import Admin

    admin = db_session.query(Admin).filter(
        Admin.username == "admin_test"
    ).first()

    result.status = ResultStatus.PUBLISHED
    result.published_at = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    )
    result.published_by_admin_id = admin.id
    result.notification_sent = True

    db_session.commit()
    db_session.refresh(result)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/results/{result.id}/void",
        params={"reason": "????? ????? ????????"},
        headers=headers,
    )

    assert response.status_code == 200

    db_session.refresh(result)

    assert result.status == ResultStatus.VOIDED
    assert result.published_at is None
    assert result.published_by_admin_id is None
    assert result.notification_sent is False
    assert result.change_reason == "????? ????? ????????"

def test_publish_bulk_publishes_only_unpublished_results(
    client,
    db_session,
    super_admin_token,
):
    from datetime import datetime, timezone

    user1, exam = _create_user_and_exam(db_session)

    user2 = User(
        bale_user_id=100000002,
        phone_number="09121111112",
        national_code="2222222222",
        first_name="Test2",
        last_name="User2",
    )
    user3 = User(
        bale_user_id=100000003,
        phone_number="09121111113",
        national_code="3333333333",
        first_name="Test3",
        last_name="User3",
    )

    db_session.add_all([user2, user3])
    db_session.commit()
    db_session.refresh(user2)
    db_session.refresh(user3)

    result1 = _create_result(db_session, user1, exam, score=80)
    result2 = _create_result(db_session, user2, exam, score=70)

    previous_published_at = datetime(2026, 9, 2, 12, 30, tzinfo=timezone.utc)

    result3 = Result(
        user_id=user3.id,
        exam_id=exam.id,
        score=90,
        is_passed=True,
        status=ResultStatus.PUBLISHED,
        published_at=previous_published_at,
        published_by_admin_id=None,
    )

    db_session.add(result3)
    db_session.commit()
    db_session.refresh(result3)

    original_published_at = result3.published_at
    original_published_by_admin_id = result3.published_by_admin_id

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        "/api/results/publish-bulk",
        params={"exam_id": str(exam.id)},
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["published_count"] == 2

    db_session.refresh(result1)
    db_session.refresh(result2)
    db_session.refresh(result3)

    assert result1.status == ResultStatus.PUBLISHED
    assert result2.status == ResultStatus.PUBLISHED
    assert result3.status == ResultStatus.PUBLISHED

    assert result1.published_at is not None
    assert result2.published_at is not None

    assert result3.published_at == original_published_at
    assert result3.published_by_admin_id == original_published_by_admin_id

    result3_history = (
        db_session.query(ResultHistory)
        .filter(ResultHistory.result_id == result3.id)
        .all()
    )

    assert result3_history == []


def test_publish_bulk_creates_history_for_each_result(
    client,
    db_session,
    super_admin_token,
):
    user1, exam = _create_user_and_exam(db_session)

    user2 = User(
        bale_user_id=100000004,
        phone_number="09121111114",
        national_code="4444444444",
        first_name="Test4",
        last_name="User4",
    )

    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)

    result1 = _create_result(db_session, user1, exam, score=80)
    result2 = _create_result(db_session, user2, exam, score=65)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        "/api/results/publish-bulk",
        params={"exam_id": str(exam.id)},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["published_count"] == 2

    histories = (
        db_session.query(ResultHistory)
        .filter(
            ResultHistory.result_id.in_([result1.id, result2.id])
        )
        .order_by(ResultHistory.changed_at.asc())
        .all()
    )

    assert len(histories) == 2

    history_by_result = {
        history.result_id: history
        for history in histories
    }

    history1 = history_by_result[result1.id]
    history2 = history_by_result[result2.id]

    assert history1.previous_score == 80
    assert history1.new_score == 80
    assert history1.previous_status == ResultStatus.RECORDED.value
    assert history1.new_status == ResultStatus.PUBLISHED.value
    assert history1.changed_by_admin_id is not None

    assert history2.previous_score == 65
    assert history2.new_score == 65
    assert history2.previous_status == ResultStatus.RECORDED.value
    assert history2.new_status == ResultStatus.PUBLISHED.value
    assert history2.changed_by_admin_id is not None

def test_list_results_without_filters(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    _create_result(db_session, user, exam, score=80)

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        "/api/results",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["exam_id"] == str(exam.id)
    assert float(data[0]["score"]) == 80


def test_list_results_with_exam_and_status_filters(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)

    result = _create_result(
        db_session,
        user,
        exam,
        score=80,
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.get(
        "/api/results",
        params={
            "exam_id": str(exam.id),
            "status": ResultStatus.RECORDED.value,
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(result.id)
    assert data[0]["exam_id"] == str(exam.id)
    assert data[0]["status"] == ResultStatus.RECORDED.value


def test_update_result_status_to_published(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(
        db_session,
        user,
        exam,
        score=80,
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "status": ResultStatus.PUBLISHED.value,
            "change_reason": "انتشار نتیجه",
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == ResultStatus.PUBLISHED.value
    assert data["published_at"] is not None

    db_session.refresh(result)

    assert result.status == ResultStatus.PUBLISHED
    assert result.published_at is not None
    assert result.published_by_admin_id is not None


def test_unpublish_result_not_found(
    client,
    db_session,
    super_admin_token,
):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/results/{uuid.uuid4()}/unpublish",
        headers=headers,
    )

    assert response.status_code == 404


def test_void_result_not_found(
    client,
    db_session,
    super_admin_token,
):
    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.post(
        f"/api/results/{uuid.uuid4()}/void",
        params={"reason": "نتیجه نامعتبر"},
        headers=headers,
    )

    assert response.status_code == 404


def test_get_result_history(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(
        db_session,
        user,
        exam,
        score=75,
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    update_response = client.patch(
        f"/api/results/{result.id}",
        json={
            "score": "85",
            "change_reason": "اصلاح نمره",
        },
        headers=headers,
    )

    assert update_response.status_code == 200

    response = client.get(
        f"/api/results/{result.id}/history",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()



def test_update_result_status_to_reviewed(
    client,
    db_session,
    super_admin_token,
):
    user, exam = _create_user_and_exam(db_session)
    result = _create_result(
        db_session,
        user,
        exam,
        score=80,
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    response = client.patch(
        f"/api/results/{result.id}",
        json={
            "status": ResultStatus.REVIEWED.value,
            "change_reason": "????? ?????",
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == ResultStatus.REVIEWED.value
    assert data["published_at"] is None

    db_session.refresh(result)

    assert result.status == ResultStatus.REVIEWED
    assert result.published_at is None
    assert result.published_by_admin_id is None
