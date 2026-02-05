from pydantic import BaseModel
from typing import Optional, Dict, Any


class ProcessRequest(BaseModel):
    system_prompt: str
    user_prompt: str


class ProcessResponse(BaseModel):
    response: str


class OnboardingExtractRequest(BaseModel):
    question: str
    answer: str
    context: Optional[Dict[str, Any]] = None


class ExtractedData(BaseModel):
    mouse_keyboard_skill: Optional[str] = None
    programming_experience: Optional[str] = None
    child_age: Optional[int] = None
    child_name: Optional[str] = None


class OnboardingExtractResponse(BaseModel):
    extracted: ExtractedData
    needs_clarification: bool
    clarification_question: Optional[str] = None

