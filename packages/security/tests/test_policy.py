import pytest

from security.policy import PolicyViolation, ToolPolicy


def test_allows_tool_not_denied():
    policy = ToolPolicy(denied_tools={"http_post"})
    policy.check("calculator")  # does not raise


def test_denies_listed_tool():
    policy = ToolPolicy(denied_tools={"http_post"})
    with pytest.raises(PolicyViolation, match="http_post"):
        policy.check("http_post")


def test_empty_policy_allows_everything():
    policy = ToolPolicy()
    policy.check("anything")
