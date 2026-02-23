from __future__ import annotations

from immcad_api.policy.compliance import should_refuse_for_policy


def test_should_refuse_for_policy_blocked_phrases() -> None:
    blocked_messages = [
        "Please represent me before the IRB.",
        "Can you file my immigration application for me?",
        "Act as my counsel and submit forms for me.",
        "Guarantee that I will get my visa approved.",
    ]

    for message in blocked_messages:
        assert should_refuse_for_policy(message)


def test_should_refuse_for_policy_allows_information_request() -> None:
    assert not should_refuse_for_policy(
        "Summarize IRPA inadmissibility grounds in plain language."
    )
