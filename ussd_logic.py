from sqlalchemy.orm import Session
import models
from sms_engine import send_sms_nudge

def get_or_create_user(db: Session, phone_number: str):
    user = db.query(models.User).filter(models.User.phone_number == phone_number).first()
    if not user:
        user = models.User(phone_number=phone_number)
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # init progress (Starting at Module order 1, step 0)
        progress = models.UserProgress(user_id=user.id, current_module_id=1, current_lesson_step=0)
        db.add(progress)
        db.commit()
    return user

def process_ussd(phone_number: str, text: str, db: Session) -> str:
    """
    Core USSD Logic responding to Africa's Talking format.
    Returns strings starting with 'CON ' to continue or 'END ' to terminate.
    """
    user = get_or_create_user(db, phone_number)
    
    # Split text by '*' to get the input sequence
    inputs = text.split('*') if text else []
    
    if not user.is_registered:
        return handle_registration(user, inputs, db)
    
    # User is registered, handle curriculum navigation
    return handle_curriculum(user, inputs, db)

def handle_registration(user: models.User, inputs: list, db: Session) -> str:
    if len(inputs) == 0 or inputs[0] == "":
        return "CON Welcome to Ikwéé: The Light of Learning.\nPlease reply with your Name to register:"
    
    if len(inputs) == 1:
        # Save name and complete registration
        user.name = inputs[0]
        user.is_registered = True
        db.commit()
        send_sms_nudge(user.phone_number, f"Welcome to the platform, {user.name}! Dial the shortcode anytime to learn.")
        return f"CON Registration successful, {user.name}!\n1. Start Learning\n2. Exit"
    
    if len(inputs) == 2:
        if inputs[1] == "1":
            return handle_curriculum(user, [], db)
        else:
            return "END Thank you for visiting."

def handle_curriculum(user: models.User, inputs: list, db: Session) -> str:
    progress = db.query(models.UserProgress).filter(models.UserProgress.user_id == user.id).first()
    
    # Get current module from DB
    module = db.query(models.Module).filter(models.Module.order_seq == progress.current_module_id).first()
    
    if not module:
        return "END Congratulations! You have completed all currently available modules. We will SMS you when more are added."
        
    if len(inputs) == 0 or inputs[0] == "":
        return f"CON Welcome back {user.name}.\nCurrent: {module.title}\n1. Continue Lesson\n2. Exit"
        
    if inputs[-1] == "2" and len(inputs) == 1:
        return "END Goodbye!"
        
    if inputs[0] == "1":
        return serve_lesson(progress, module, inputs[1:], db, user.phone_number)
        
    return "CON Invalid choice.\n1. Continue Lesson\n2. Exit"

def serve_lesson(progress: models.UserProgress, module: models.Module, lesson_inputs: list, db: Session, phone_number: str) -> str:
    # Query current lesson from DB
    lesson = db.query(models.Lesson).filter(
        models.Lesson.module_id == module.id,
        models.Lesson.step_seq == progress.current_lesson_step
    ).first()
    
    if not lesson:
        # Step beyond module lessons -> module complete
        progress.current_module_id += 1
        progress.current_lesson_step = 0
        db.commit()
        
        # Send celebratory SMS notification
        send_sms_nudge(phone_number, f"Congratulations! You just completed {module.title}. Keep up the great work!")
        return "END Module completed! Dial again to start the next module."

    # If it's a content page
    if lesson.lesson_type == "content":
        if len(lesson_inputs) == 0:
            return f"CON {lesson.text_content}\n\n1. Next"
        if lesson_inputs[-1] == "1":
            progress.current_lesson_step += 1
            db.commit()
            return "END Lesson read. Dial again to continue learning."

    # If it's a quiz
    if lesson.lesson_type == "quiz":
        if len(lesson_inputs) == 0:
            return f"CON QUIZ:\n{lesson.text_content}"
            
        answer = lesson_inputs[-1]
        quiz_data = lesson.quiz # Relationship loads automatically
        
        if answer == quiz_data.correct_answer:
            progress.current_lesson_step += 1
            db.commit()
            return "END Correct! Dial again for your next lesson."
        else:
            # Trigger SMS Feedback
            send_sms_nudge(phone_number, f"Review tip: {quiz_data.wrong_feedback}")
            return f"END Incorrect. We sent a tip via SMS. \nDial again to retry."
    
    return "END Error loading lesson configuration."
