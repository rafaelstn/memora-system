from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.core.assistant import ask_assistant
from app.models.user import User

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    repo_name: str
    max_chunks: int = 5


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]


@router.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = ask_assistant(
        db=db,
        question=request.question,
        repo_name=request.repo_name,
        max_chunks=request.max_chunks,
        org_id=user.org_id,
    )
    return result
