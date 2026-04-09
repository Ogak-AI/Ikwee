from fastapi import FastAPI, Depends, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
import database
import models
import ussd_logic
import logging
import traceback

# Configure logging so all USSD requests and errors are visible in Render logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Automatically create sqlite tables based on models
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Ikwéé Production Platform")

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"status": "Production Webhook is Live"}

@app.head("/")
def head_root():
    return Response(status_code=200)

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    """
    Render health-check endpoint. Keeps the free-tier service warm
    and confirms the DB connection is alive.
    """
    try:
        db = next(database.get_db())
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "degraded", "error": str(e)}

@app.head("/health")
def head_health():
    return Response(status_code=200)

@app.post("/ussd")
async def ussd_callback(request: Request, db: Session = Depends(database.get_db)):
    """
    Africa's Talking webhooks send application/x-www-form-urlencoded data.
    """
    form_data = await request.form()

    session_id   = form_data.get("sessionId", "")
    service_code = form_data.get("serviceCode", "")
    phone_number = form_data.get("phoneNumber", "")
    text         = form_data.get("text", "")

    logger.info(f"USSD | session={session_id} | phone={phone_number} | code={service_code} | text='{text}'")

    if not phone_number:
        logger.warning("USSD request received with no phoneNumber — returning END")
        return Response(content="END Missing Phone Number", media_type="text/plain")

    try:
        response_text = ussd_logic.process_ussd(phone_number, text, db)
        logger.info(f"USSD | response -> {response_text[:60]}")
        return Response(content=response_text.strip(), media_type="text/plain")
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"USSD ERROR | Exception: {e}\n{error_trace}")
        return Response(content="END System error. Please try again later.", media_type="text/plain")

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
