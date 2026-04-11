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

@app.get("/debug/db_status")
def db_status(db: Session = Depends(database.get_db)):
    """
    Diagnostic route to check the number of records in the database.
    """
    return {
        "users": db.query(models.User).count(),
        "modules": db.query(models.Module).count(),
        "lessons": db.query(models.Lesson).count(),
        "quizzes": db.query(models.Quiz).count()
    }

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

@app.post("/sms")
async def sms_callback(request: Request, db: Session = Depends(database.get_db)):
    """
    Africa's Talking incoming SMS webhook.
    """
    import subscription_logic
    from sms_engine import send_sms_nudge

    form_data = await request.form()
    
    from_number = form_data.get("from", "")
    text        = form_data.get("text", "")
    link_id     = form_data.get("linkId", "") # Used for premium billing responses
    
    logger.info(f"SMS RECV | from={from_number} | text='{text}' | link_id={link_id}")

    if not from_number or not text:
        return Response(status_code=400)

    try:
        response_msg, keyword = subscription_logic.handle_incoming_sms(from_number, text, db)
        
        # Send a response back to the user. 
        # If 'keyword' and 'link_id' are present, this will trigger the Premium charge.
        send_sms_nudge(from_number, response_msg, keyword=keyword, link_id=link_id)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"SMS CALLBACK ERROR: {e}")
        return Response(status_code=500)

@app.post("/admin/seed_curriculum")
def seed_curriculum(db: Session = Depends(database.get_db)):
    """
    Admin route to inject curriculum from JSON files into the database.
    """
    import json
    import os

    # Clear existing data
    db.execute(text("DELETE FROM quizzes"))
    db.execute(text("DELETE FROM lessons"))
    db.execute(text("DELETE FROM modules"))
    db.commit()

    CURRICULUM_DIR = "curriculum"
    files = [f for f in os.listdir(CURRICULUM_DIR) if f.endswith(".json")]
    
    total_modules = 0
    total_lessons = 0

    # Start order_seq globally or reset per file? 
    # Let's keep a global counter for modules to ensure unique keys
    module_global_seq = 1

    for filename in files:
        filepath = os.path.join(CURRICULUM_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            for mod_data in data.get("modules", []):
                module = models.Module(
                    title=mod_data["title"], 
                    order_seq=module_global_seq
                )
                db.add(module)
                db.commit()
                db.refresh(module)
                module_global_seq += 1
                total_modules += 1
                
                for lesson_data in mod_data.get("lessons", []):
                    lesson = models.Lesson(
                        module_id=module.id,
                        step_seq=lesson_data["step_seq"],
                        lesson_type=lesson_data["type"],
                        text_content=lesson_data["text"]
                    )
                    db.add(lesson)
                    db.commit()
                    db.refresh(lesson)
                    total_lessons += 1
                    
                    if lesson_data["type"] == "quiz":
                        quiz = models.Quiz(
                            lesson_id=lesson.id,
                            correct_answer=lesson_data["answer"],
                            wrong_feedback=lesson_data["feedback"]
                        )
                        db.add(quiz)
                        db.commit()
    
    return {
        "status": "Success", 
        "modules_seeded": total_modules, 
        "lessons_seeded": total_lessons,
        "files_processed": files
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
