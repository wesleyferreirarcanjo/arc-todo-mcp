import pytest

from app.caller_auth import caller_token_scope


@pytest.fixture
def caller_auth():
    with caller_token_scope("token-abc"):
        yield "token-abc"
