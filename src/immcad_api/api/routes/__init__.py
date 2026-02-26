from immcad_api.api.routes.cases import build_case_router, build_case_router_disabled
from immcad_api.api.routes.chat import build_chat_router
from immcad_api.api.routes.documents import build_documents_router
from immcad_api.api.routes.lawyer_research import (
    build_lawyer_research_router,
    build_lawyer_research_router_disabled,
)

__all__ = [
    "build_case_router",
    "build_case_router_disabled",
    "build_chat_router",
    "build_documents_router",
    "build_lawyer_research_router",
    "build_lawyer_research_router_disabled",
]
