from pydantic import BaseModel


class FAQCreate(BaseModel):
    question: str
    answer: str
    target_role: str