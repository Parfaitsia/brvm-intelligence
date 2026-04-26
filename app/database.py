from sqlalchemy import create_engine, Column, String, Float, Integer, Date, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://brvm_user:brvm_pass_2024@localhost:5432/brvm_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class CoursAction(Base):
    __tablename__ = "cours_actions"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    date         = Column(Date, nullable=False)
    ticker       = Column(String(20), nullable=False)
    cloture      = Column(Float)
    cours_veille = Column(Float)
    volume       = Column(Integer, default=0)
    variation    = Column(String(20))
    source       = Column(String(50))
    created_at   = Column(DateTime, default=datetime.utcnow)


class Fondamentaux(Base):
    __tablename__ = "fondamentaux"

    ticker         = Column(String(20), primary_key=True)
    nom_societe    = Column(String(200))
    secteur        = Column(String(100))
    per            = Column(Float)
    pbr            = Column(Float)
    roe            = Column(Float)
    rendement_div  = Column(Float)
    capitalisation = Column(Float)
    mis_a_jour     = Column(Date)


class Recommandation(Base):
    __tablename__ = "recommandations"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    date           = Column(Date, nullable=False)
    ticker         = Column(String(20), nullable=False)
    signal         = Column(String(10))   # BUY / HOLD / SELL
    confiance      = Column(Integer)       # 0-100
    score_final    = Column(Float)
    explication    = Column(Text)
    created_at     = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Crée toutes les tables si elles n'existent pas."""
    Base.metadata.create_all(engine)
    print("✅ Base de données initialisée")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()