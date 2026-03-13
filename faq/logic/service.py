# faq/logic/service.py
from db.tables import FAQ
from fastapi import HTTPException

async def create_faq_logic(question: str, answer: str, target_role: str):
    new_faq = FAQ(question=question, answer=answer, target_role=target_role)
    await new_faq.save()
    return new_faq

async def get_faqs_by_role(role: str):
    # Logic: Show FAQs meant specifically for the user's role OR marked for 'both'
    return await FAQ.select().where(
        (FAQ.target_role == role) | (FAQ.target_role == 'both')
    ).order_by(FAQ.created_at, ascending=False).run()

async def admin_get_all_faqs():
    # Admin sees everything for management
    return await FAQ.select().order_by(FAQ.created_at, ascending=False).run()

async def delete_faq_logic(faq_id: str):
    faq = await FAQ.objects().get(FAQ.id == faq_id).run()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    await faq.remove()
    return {"message": "FAQ deleted successfully"}