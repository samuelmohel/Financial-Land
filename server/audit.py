# server/audit.py
import datetime
import json
from sqlalchemy import create_engine, Column, Integer, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from server.config import DATABASE_URL

Base = declarative_base()

class Audit(Base):
    __tablename__ = "audits"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(Text, nullable=True)
    action = Column(Text)
    payload = Column(Text)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, future=True)

def init_db():
    Base.metadata.create_all(engine)

def log(action: str, payload: dict, user_id: str | None = None):
    s = SessionLocal()
    a = Audit(action=action, payload=json.dumps(payload), user_id=user_id)
    s.add(a)
    s.commit()
    s.close()
    return a.id
