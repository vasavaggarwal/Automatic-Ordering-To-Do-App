# models.py
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean
)
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure db directory exists
os.makedirs("db", exist_ok=True)

# SQLite file path
DB_URL = "sqlite:///db/tasks.db"

# SQLAlchemy base and engine setup
Base = declarative_base()
engine = create_engine(DB_URL, echo=False, future=True)
Session = sessionmaker(bind=engine)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)           # Task title
    category = Column(String, nullable=False)        # Necessary / College / Home / Awaragardi
    due_datetime = Column(DateTime, nullable=False)  # Due date & time
    locked = Column(Boolean, default=False)          # True if manually fixed/locked in main list
    fixed_pos = Column(Integer, nullable=True)       # If locked=True, the main-list slot (0-based)
    part_label = Column(String, nullable=True)       # e.g. "Part 1"
    is_done = Column(Boolean, default=False)         # True when task marked done
    is_gym = Column(Boolean, default=False)          # True for Gym rows/special tasks
    in_main = Column(Boolean, default=False)         # True if task currently placed in Main workspace
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def as_dict(self):
        """Return a plain dict useful for logic/rendering."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "due_datetime": self.due_datetime,
            "locked": self.locked,
            "fixed_pos": self.fixed_pos,
            "part_label": self.part_label,
            "is_done": self.is_done,
            "is_gym": self.is_gym,
            "in_main": self.in_main,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

if __name__ == "__main__":
    # Create tables (runs once). Use this to initialize the DB.
    Base.metadata.create_all(engine)
    print("Database & tables created at db/tasks.db")
