import pytest

from app.board_scope import reset_last_board
from app.caller_auth import caller_token_scope


@pytest.fixture
def caller_auth():
    reset_last_board()
    with caller_token_scope("token-abc"):
        yield "token-abc"
    reset_last_board()
