from sqlalchemy.orm import Session
import models
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Keywords that trigger subscriptions
COURSE_KEYWORDS = {
    "JAMB": "JAMB Prep",
    "WAEC": "WAEC Prep"
}

def get_or_create_user(db: Session, phone_number: str):
    user = db.query(models.User).filter(models.User.phone_number == phone_number).first()
    if not user:
        user = models.User(phone_number=phone_number)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def handle_incoming_sms(phone_number: str, text: str, db: Session):
    """
    Main logic for processing incoming SMS commands.
    Returns (response_message, keyword_used)
    """
    text = text.strip().upper()
    user = get_or_create_user(db, phone_number)
    
    # Check for unsubscription
    if text in ["STOP", "END", "CANCEL", "UNSUBSCRIBE"]:
        user.is_subscribed = False
        db.commit()
        return "You have been unsubscribed from Ikwéé daily updates. Send JAMB or WAEC to join again.", None

    # Check for course subscription
    matched_keyword = None
    for kw in COURSE_KEYWORDS:
        if kw in text:
            matched_keyword = kw
            break
            
    if matched_keyword:
        user.is_subscribed = True
        user.subscription_type = COURSE_KEYWORDS[matched_keyword]
        # Set expiry to 30 days from now
        user.subscription_expiry = int((datetime.now() + timedelta(days=30)).timestamp())
        db.commit()
        
        # Ensure progress record exists
        progress = db.query(models.UserProgress).filter(models.UserProgress.user_id == user.id).first()
        if not progress:
            progress = models.UserProgress(user_id=user.id, current_module_id=1, current_lesson_step=0)
            db.add(progress)
            db.commit()
            
        return f"Welcome! You are now subscribed to {user.subscription_type}. You will receive your first lesson shortly.", matched_keyword

    return "Welcome to Ikwéé! Send JAMB or WAEC to subscribe for daily lessons using your airtime.", None

def get_next_lesson_for_user(user: models.User, db: Session):
    """
    Fetches the next lesson content for the user based on their current progress.
    """
    progress = db.query(models.UserProgress).filter(models.UserProgress.user_id == user.id).first()
    if not progress:
        return None
        
    module = db.query(models.Module).filter(models.Module.order_seq == progress.current_module_id).first()
    if not module:
        return None
        
    lesson = db.query(models.Lesson).filter(
        models.Lesson.module_id == module.id,
        models.Lesson.step_seq == progress.current_lesson_step
    ).first()
    
    if not lesson:
        # Move to next module if current step is out of bounds
        progress.current_module_id += 1
        progress.current_lesson_step = 0
        db.commit()
        return get_next_lesson_for_user(user, db)
        
    return lesson
