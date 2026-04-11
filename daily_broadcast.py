import os
import logging
from datetime import datetime
import database
import models
import subscription_logic
from sms_engine import send_sms_nudge

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run_broadcast():
    """
    Main broadcast loop to be triggered daily via a Cron job (e.g., on Render or GitHub Actions).
    """
    db = next(database.get_db())
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Fetch all active subscribers who haven't received a message today
    subscribers = db.query(models.User).filter(
        models.User.is_subscribed == True,
        (models.User.last_broadcast_date != today_str) | (models.User.last_broadcast_date == None)
    ).all()
    
    logger.info(f"Broadcast starting for {len(subscribers)} subscribers.")
    
    for user in subscribers:
        try:
            # 2. Get the next lesson for this user
            lesson = subscription_logic.get_next_lesson_for_user(user, db)
            
            if not lesson:
                logger.info(f"No content found for {user.phone_number} (Module/Step sequence complete?)")
                continue
                
            # 3. Format the message
            # For Premium Broadast, we usually use the configured Shortcode and Keyword.
            # keyword = user.subscription_type.split(' ')[0].upper() # Extract keyword from JAMB Prep -> JAMB
            
            content = f"Today's Lesson ({user.subscription_type}):\n{lesson.text_content}"
            
            # 4. Send the SMS
            # Note: For daily broadcast, we don't have a linkId (those are for on-demand responses).
            # Daily broadcast charges are typically handled by the Subscription Service on AT's end,
            # or by sending a Bulk SMS if the subscription was pre-paid.
            success = send_sms_nudge(user.phone_number, content)
            
            if success:
                # 5. Increment progress and update broadcast date
                progress = db.query(models.UserProgress).filter(models.UserProgress.user_id == user.id).first()
                progress.current_lesson_step += 1
                user.last_broadcast_date = today_str
                db.commit()
                logger.info(f"Broadcast sent successfully to {user.phone_number}")
            else:
                logger.error(f"Failed to send broadcast to {user.phone_number}")
                
        except Exception as e:
            logger.error(f"Error processing broadcast for {user.phone_number}: {e}")
            db.rollback()

if __name__ == "__main__":
    run_broadcast()
