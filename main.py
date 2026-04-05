from fastapi import FastAPI, Depends, Request, Response, BackgroundTasks
from sqlalchemy.orm import Session
import database
import models
import ussd_logic

# Automatically create sqlite tables based on models
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Ikwéé Production Platform")

@app.get("/")
def read_root():
    return {"status": "Production Webhook is Live"}

@app.post("/ussd")
async def ussd_callback(request: Request, db: Session = Depends(database.get_db)):
    """
    Africa's Talking webhooks send application/x-www-form-urlencoded data.
    """
    form_data = await request.form()
    
    session_id = form_data.get("sessionId")
    service_code = form_data.get("serviceCode")
    phone_number = form_data.get("phoneNumber", "")
    text = form_data.get("text", "")
    
    if not phone_number:
        return Response(content="END Missing Phone Number", media_type="text/plain")
        
    response_text = ussd_logic.process_ussd(phone_number, text, db)
    return Response(content=response_text, media_type="text/plain")

@app.post("/admin/seed_curriculum")
def seed_curriculum(db: Session = Depends(database.get_db)):
    """
    Admin route to inject sample curriculum into the live database.
    This replaces the old mock file.
    """
    existing_mod = db.query(models.Module).first()
    if existing_mod:
        return {"status": "Database already contains curriculum"}
        
    # Module 1
    m1 = models.Module(title="Module 1: TVET Agritech", order_seq=1)
    db.add(m1)
    db.commit()
    db.refresh(m1)
    
    # Add Lesson content
    l1 = models.Lesson(module_id=m1.id, step_seq=0, lesson_type="content", text_content="Lesson 1: Crops grow best when soil pH is balanced between 6 and 7.")
    # Add Quiz
    l2 = models.Lesson(module_id=m1.id, step_seq=1, lesson_type="quiz", text_content="What is ideal soil pH?\n1. 3-4\n2. 6-7\n3. 9-10")
    db.add_all([l1, l2])
    db.commit()
    db.refresh(l2)
    
    # Save Quiz specifics tied to lesson l2
    q1 = models.Quiz(lesson_id=l2.id, correct_answer="2", wrong_feedback="Acidity (low pH) stunts root growth. Ideal is 6-7.")
    db.add(q1)
    db.commit()
    
    return {"status": "Database seeded with Module 1!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
