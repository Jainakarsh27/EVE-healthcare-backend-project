from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_webhook_signature,
    hash_password,
    verify_password,
    verify_webhook_signature,
)


def test_password_hashing_and_verification():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_encoding_decoding():
    subject = "12345678-1234-5678-1234-567812345678"
    role = "USER"
    email = "test@example.com"

    token = create_access_token(subject=subject, role=role, email=email)
    payload = decode_access_token(token)

    assert payload["sub"] == subject
    assert payload["role"] == role
    assert payload["email"] == email


def test_webhook_hmac_signature_verification():
    payload = b'{"event_id": "evt_100", "status": "SUCCESS"}'
    secret = "test_webhook_secret_key"

    signature = generate_webhook_signature(payload, secret)
    assert len(signature) == 64  # SHA256 hex length

    assert verify_webhook_signature(payload, signature, secret) is True
    assert verify_webhook_signature(payload, "invalid_signature", secret) is False
    assert verify_webhook_signature(b'{"modified": true}', signature, secret) is False
