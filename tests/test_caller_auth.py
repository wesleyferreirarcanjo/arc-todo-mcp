from app.caller_auth import (
    MISSING_CALLER_TOKEN_MESSAGE,
    extract_token_from_headers,
    get_session_token,
    normalize_caller_token,
    remember_session_token,
    require_caller_token,
    reset_session_tokens,
    resolve_caller_token,
)


def setup_function() -> None:
    reset_session_tokens()


def test_normalize_strips_bearer_and_quotes() -> None:
    jwt = "eyJhbGciOiJIUzI1NiJ9.payload.sig"
    assert normalize_caller_token(f"Bearer {jwt}") == jwt
    assert normalize_caller_token(f'  "{jwt}"  ') == jwt
    assert normalize_caller_token("   ") is None


def test_extract_token_from_x_arc_todo_token() -> None:
    jwt = "eyJhbGciOiJIUzI1NiJ9.payload.sig"
    assert extract_token_from_headers({"x-arc-todo-token": jwt}) == jwt
    assert extract_token_from_headers({"x-api-key": f"Bearer {jwt}"}) == jwt
    assert extract_token_from_headers({"authorization": f"Bearer {jwt}"}) == jwt


def test_session_token_requires_session_id() -> None:
    jwt = "session-jwt"
    remember_session_token(None, jwt)
    remember_session_token("sess-1", jwt)
    assert get_session_token(None) is None
    assert get_session_token("sess-1") == jwt
    assert get_session_token("other") is None


def test_resolve_prefers_set_caller_auth_argument() -> None:
    headers = {
        "authorization": "Bearer header-jwt",
        "mcp-session-id": "sess-1",
    }
    remember_session_token("sess-1", "session-jwt")
    token = resolve_caller_token(
        headers,
        tool_name="set_caller_auth",
        arguments={"token": "inline-jwt"},
    )
    assert token == "inline-jwt"


def test_empty_input_schema_includes_arc_todo_token() -> None:
    from app.tool_registry import EmptyInput

    schema = EmptyInput.model_json_schema()
    assert "arc_todo_token" in schema["properties"]


def test_resolve_falls_back_to_session_when_headers_empty() -> None:
    remember_session_token("sess-9", "sticky-jwt")
    token = resolve_caller_token(
        {"mcp-session-id": "sess-9"},
        tool_name="list_organizations",
        arguments={},
    )
    assert token == "sticky-jwt"


def test_resolve_arc_todo_token_on_any_tool() -> None:
    token = resolve_caller_token(
        {},
        tool_name="list_organizations",
        arguments={"arc_todo_token": "per-call-jwt"},
    )
    assert token == "per-call-jwt"


def test_require_caller_token_mentions_per_call_argument() -> None:
    from app.caller_auth import caller_token_scope

    with caller_token_scope(None):
        try:
            require_caller_token()
        except ValueError as exc:
            assert "arc_todo_token" in str(exc)
            assert str(exc).startswith("Missing Authorization bearer token")
            assert exc.args[0] == MISSING_CALLER_TOKEN_MESSAGE
        else:
            raise AssertionError("expected ValueError")
