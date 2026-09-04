from app.core.security import validate_national_code, validate_phone_number, hash_password, verify_password


def test_valid_national_code():
    assert validate_national_code("0499370899") is True


def test_invalid_national_code_checksum():
    assert validate_national_code("1234567890") is False


def test_invalid_national_code_repeated_digits():
    assert validate_national_code("1111111111") is False


def test_invalid_national_code_length():
    assert validate_national_code("12345") is False


def test_valid_phone_number():
    assert validate_phone_number("09123456789") is True


def test_invalid_phone_number():
    assert validate_phone_number("123456") is False


def test_password_hash_and_verify():
    hashed = hash_password("MySecret123")
    assert verify_password("MySecret123", hashed) is True
    assert verify_password("WrongPass", hashed) is False

def test_create_access_token_without_extra_claims():
    from app.core.security import create_access_token, decode_access_token

    token = create_access_token("test-subject")
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "test-subject"
    assert "exp" in payload


def test_validate_national_code_remainder_greater_than_or_equal_to_two():
    from app.core.security import validate_national_code

    assert validate_national_code("1234567890") is False


def test_validate_phone_number_invalid_values():
    from app.core.security import validate_phone_number

    assert validate_phone_number("") is False
    assert validate_phone_number("12345678901") is False
    assert validate_phone_number("0912345678A") is False
    assert validate_phone_number("08123456789") is False

def test_decode_access_token_invalid_token_returns_none():
    from app.core.security import decode_access_token

    result = decode_access_token("not-a-valid-jwt")

    assert result is None
