from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    is_registered = Column(Boolean, default=False)
    name = Column(String, nullable=True)
    
    # Subscription Metadata
    is_subscribed = Column(Boolean, default=False)
    subscription_type = Column(String, nullable=True) # e.g., 'JAMB', 'WAEC'
    subscription_expiry = Column(Integer, nullable=True) # Unix timestamp or DateTime
    last_broadcast_date = Column(String, nullable=True) # To prevent multiple sends per day
    
class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    current_module_id = Column(Integer, default=1)
    current_lesson_step = Column(Integer, default=0)

# Product Database Models for Curriculum

class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    order_seq = Column(Integer, unique=True) # To know which module comes next
    
    # 1 to Many relationship with Lessons
    lessons = relationship("Lesson", back_populates="module", order_by="Lesson.step_seq")

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    step_seq = Column(Integer)
    lesson_type = Column(String) # 'content' or 'quiz'
    text_content = Column(String)
    
    module = relationship("Module", back_populates="lessons")
    quiz = relationship("Quiz", back_populates="lesson", uselist=False)

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    correct_answer = Column(String)
    wrong_feedback = Column(String)
    
    lesson = relationship("Lesson", back_populates="quiz")
