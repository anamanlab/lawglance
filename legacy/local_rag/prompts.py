"""Legacy prompt compatibility shim (deprecated).

Legacy imports remain supported, but prompt text must stay canonical with the
runtime policy prompts.
"""

from immcad_api.policy.prompts import QA_PROMPT, SYSTEM_PROMPT

__all__ = ["SYSTEM_PROMPT", "QA_PROMPT"]
