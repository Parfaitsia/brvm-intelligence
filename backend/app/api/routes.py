from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db, CoursAction, Recommandation
from app.scoring.moteur import MoteurScoring
from app.scrapers.save_cours import scrape_et_sauvegarder
from app.scoring.explainer import repondre_question, generer_resume_marche
from datetime import date
import asyncio

app = FastAPI(title="BRVM Intelligence API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str


@app.get("/")
def accueil():
    return {"message": "BRVM Intelligence API", "status": "ok", "date": str(date.today())}


@app.get("/api/cours")
def get_cours(db: Session = Depends(get_db)):
    cours = (
        db.query(CoursAction)
        .filter(CoursAction.date == date.today())
        .order_by(CoursAction.ticker)
        .all()
    )
    return [
        {
            "ticker":    c.ticker,
            "cloture":   c.cloture,
            "variation": c.variation,
            "volume":    c.volume,
            "date":      str(c.date),
        }
        for c in cours
    ]


@app.get("/api/recommandations")
def get_recommandations(db: Session = Depends(get_db)):
    recs = (
        db.query(Recommandation)
        .filter(Recommandation.date == date.today())
        .order_by(Recommandation.score_final.desc())
        .all()
    )
    return [
        {
            "ticker":      r.ticker,
            "signal":      r.signal,
            "confiance":   r.confiance,
            "score":       r.score_final,
            "explication": r.explication,
            "date":        str(r.date),
        }
        for r in recs
    ]


@app.get("/api/recommandations/top")
def get_top_recommandations(db: Session = Depends(get_db)):
    recs = (
        db.query(Recommandation)
        .filter(Recommandation.date == date.today())
        .order_by(Recommandation.score_final.desc())
        .all()
    )
    buy  = [r for r in recs if r.signal == "BUY"][:5]
    sell = [r for r in recs if r.signal == "SELL"][:3]
    hold = [r for r in recs if r.signal == "HOLD"][:5]

    def format_rec(r):
        return {
            "ticker":      r.ticker,
            "signal":      r.signal,
            "confiance":   r.confiance,
            "score":       r.score_final,
            "explication": r.explication,
        }

    return {
        "date": str(date.today()),
        "buy":  [format_rec(r) for r in buy],
        "sell": [format_rec(r) for r in sell],
        "hold": [format_rec(r) for r in hold],
    }


@app.get("/api/action/{ticker}")
def get_action(ticker: str, db: Session = Depends(get_db)):
    historique = (
        db.query(CoursAction)
        .filter(CoursAction.ticker == ticker.upper())
        .order_by(CoursAction.date.desc())
        .limit(30)
        .all()
    )
    recommandation = (
        db.query(Recommandation)
        .filter(
            Recommandation.ticker == ticker.upper(),
            Recommandation.date   == date.today()
        )
        .first()
    )
    return {
        "ticker": ticker.upper(),
        "historique": [
            {
                "date":    str(h.date),
                "cloture": h.cloture,
                "volume":  h.volume,
            }
            for h in historique
        ],
        "recommandation": {
            "signal":      recommandation.signal,
            "confiance":   recommandation.confiance,
            "score":       recommandation.score_final,
            "explication": recommandation.explication,
        } if recommandation else None,
    }


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    recs  = db.query(Recommandation).filter(Recommandation.date == date.today()).all()
    cours = db.query(CoursAction).filter(CoursAction.date == date.today()).all()

    nb_buy  = len([r for r in recs if r.signal == "BUY"])
    nb_sell = len([r for r in recs if r.signal == "SELL"])
    nb_hold = len([r for r in recs if r.signal == "HOLD"])

    return {
        "date":       str(date.today()),
        "nb_actions": len(cours),
        "nb_buy":     nb_buy,
        "nb_sell":    nb_sell,
        "nb_hold":    nb_hold,
        "sentiment":  "HAUSSIER" if nb_buy > nb_sell else "BAISSIER" if nb_sell > nb_buy else "NEUTRE",
    }


@app.get("/api/resume")
def get_resume(db: Session = Depends(get_db)):
    """Résumé du marché généré par Groq."""
    recs    = db.query(Recommandation).filter(Recommandation.date == date.today()).all()
    nb_buy  = len([r for r in recs if r.signal == "BUY"])
    nb_sell = len([r for r in recs if r.signal == "SELL"])
    nb_hold = len([r for r in recs if r.signal == "HOLD"])
    top_buy  = [r.ticker for r in recs if r.signal == "BUY"][:3]
    top_sell = [r.ticker for r in recs if r.signal == "SELL"][:3]

    resume = generer_resume_marche(nb_buy, nb_hold, nb_sell, top_buy, top_sell)
    return {"date": str(date.today()), "resume": resume}


@app.post("/api/refresh")
async def refresh_donnees():
    """Lance manuellement le scraping + scoring."""
    await scrape_et_sauvegarder()
    moteur    = MoteurScoring()
    resultats = moteur.scorer_tous()
    moteur.sauvegarder_recommandations(resultats)
    return {"message": f"✅ {len(resultats)} actions mises à jour"}


@app.post("/api/chat")
def poser_question(req: QuestionRequest, db: Session = Depends(get_db)):
    """Chat pédagogique pour débutants — propulsé par Groq."""
    stats   = get_stats(db)
    reponse = repondre_question(req.question, stats)
    return {"question": req.question, "reponse": reponse}