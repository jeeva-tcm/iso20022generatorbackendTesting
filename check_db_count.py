
import sys
import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models.database import Base
from app.models.history import ValidationHistory

# Setup DB path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "iso_validator.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    count = db.query(func.count(ValidationHistory.id)).scalar()
    print(f"Total records in DB: {count}")
    
    # Check if there are records older than the latest 100
    latest_100 = db.query(ValidationHistory).order_by(ValidationHistory.timestamp.desc()).limit(100).all()
    if len(latest_100) > 0:
        oldest_visible = latest_100[-1].timestamp
        print(f"Oldest visible record timestamp: {oldest_visible}")
        
        older_count = db.query(func.count(ValidationHistory.id)).filter(ValidationHistory.timestamp < oldest_visible).scalar()
        print(f"Number of records OLDER than the visible 100: {older_count}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
