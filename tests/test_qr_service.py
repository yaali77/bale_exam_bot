import os
import uuid

from app.services.qr_service import (
    generate_verification_code,
    generate_qr_image,
)
from app.config import settings


def test_generate_verification_code():
    code = generate_verification_code()

    assert isinstance(code, str)
    assert len(code) == 32

    # باید یک UUID hex معتبر باشد
    parsed = uuid.UUID(code)
    assert parsed.hex == code


def test_generate_verification_code_is_unique():
    code1 = generate_verification_code()
    code2 = generate_verification_code()

    assert code1 != code2


def test_generate_qr_image(tmp_path, monkeypatch):
    monkeypatch.setattr(
        settings,
        "QR_STORAGE_PATH",
        str(tmp_path),
    )
    monkeypatch.setattr(
        settings,
        "PUBLIC_BASE_URL",
        "https://example.com",
    )

    verification_code = "test-verification-code"

    file_path = generate_qr_image(verification_code)

    assert os.path.exists(file_path)
    assert os.path.isfile(file_path)
    assert file_path.endswith(f"{verification_code}.png")

    assert os.path.getsize(file_path) > 0


def test_generate_qr_image_creates_storage_directory(
    tmp_path,
    monkeypatch,
):
    qr_directory = tmp_path / "qr_codes"

    monkeypatch.setattr(
        settings,
        "QR_STORAGE_PATH",
        str(qr_directory),
    )
    monkeypatch.setattr(
        settings,
        "PUBLIC_BASE_URL",
        "https://example.com",
    )

    verification_code = "directory-test"

    assert not qr_directory.exists()

    file_path = generate_qr_image(verification_code)

    assert qr_directory.exists()
    assert qr_directory.is_dir()
    assert os.path.exists(file_path)