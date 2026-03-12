# faq/logic/service.py
from db.tables import FAQ
from fastapi import HTTPException

async def create_faq_logic(question: str, answer: str):
    new_faq = FAQ(question=question, answer=answer)
    await new_faq.save()
    return new_faq

async def get_all_faqs_logic():
    return await FAQ.select().order_by(FAQ.created_at, ascending=False).run()

async def delete_faq_logic(faq_id: str):
    faq = await FAQ.objects().get(FAQ.id == faq_id).run()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    await faq.remove()
    return {"message": "FAQ deleted successfully"}