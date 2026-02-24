from __future__ import annotations

from immcad_api.policy.compliance import should_refuse_for_policy


def test_should_refuse_for_policy_blocked_phrases() -> None:
    blocked_messages = [
        "Please represent me before the IRB.",
        "Can you represent my case and appear for me?",
        "Be my representative for this hearing.",
        "Please handle my appeal hearing for me.",
        "Can you argue this case for me at the tribunal?",
        "Can you file my immigration application for me?",
        "Please submit my forms on my behalf.",
        "Can you submit my paperwork for me?",
        "Please complete my application forms and file them.",
        "Act as my counsel and submit forms for me.",
        "Give me a personalized strategy for my case.",
        "What is a tailored legal plan for my application?",
        "Guarantee that I will get my visa approved.",
        "Can you guarantee my PR approval?",
        "Can you promise my citizenship approval?",
        "Assure me that I will be approved for PR.",
    ]

    for message in blocked_messages:
        assert should_refuse_for_policy(message)


def test_should_refuse_for_policy_allows_information_request() -> None:
    allowed_messages = [
        "Summarize IRPA inadmissibility grounds in plain language.",
        "What are common strategies people consider for Express Entry?",
        "What does legal representation generally include in Canada?",
        "Can you explain how to submit an application in general terms?",
        "What factors can affect visa approval rates?",
        "What does the phrase 'on my behalf' mean in immigration paperwork?",
        "Are outcomes ever guaranteed in Canadian immigration law?",
        "What are common reasons PR applications are refused or approved?",
    ]

    for message in allowed_messages:
        assert not should_refuse_for_policy(message)
