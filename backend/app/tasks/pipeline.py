import asyncio
import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.scrapers.save_cours import scrape_et_sauvegarder
from app.scoring.moteur import MoteurScoring


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ligne = f"[{timestamp}] {msg}"
    print(ligne)

    os.makedirs("logs", exist_ok=True)
    with open(f"logs/pipeline_{date.today()}.log", "a", encoding="utf-8") as f:
        f.write(ligne + "\n")


async def run_pipeline():
    log("=" * 50)
    log("🚀 DÉMARRAGE DU PIPELINE QUOTIDIEN")
    log("=" * 50)

    # ── ÉTAPE 1 : Scraping ──
    log("📡 Étape 1/3 : Collecte des cours BRVM...")
    try:
        nb = await scrape_et_sauvegarder()
        log(f"✅ {nb} actions récupérées et sauvegardées")
    except Exception as e:
        log(f"❌ Erreur scraping : {e}")
        return False

    # ── ÉTAPE 2 : Scoring ──
    log("🤖 Étape 2/3 : Calcul des scores et recommandations...")
    try:
        moteur    = MoteurScoring()
        resultats = moteur.scorer_tous()
        moteur.sauvegarder_recommandations(resultats)

        buy  = len([r for r in resultats if r.signal == "BUY"])
        hold = len([r for r in resultats if r.signal == "HOLD"])
        sell = len([r for r in resultats if r.signal == "SELL"])
        log(f"✅ Scoring terminé : {buy} BUY | {hold} HOLD | {sell} SELL")
    except Exception as e:
        log(f"❌ Erreur scoring : {e}")
        return False

    # ── ÉTAPE 3 : Résumé Groq ──
    log("🧠 Étape 3/3 : Génération du résumé marché avec Groq...")
    try:
        from app.scoring.explainer import generer_resume_marche
        top_buy  = [r.ticker for r in resultats if r.signal == "BUY"]
        top_sell = [r.ticker for r in resultats if r.signal == "SELL"]
        resume   = generer_resume_marche(buy, hold, sell, top_buy, top_sell)
        log(f"📰 Résumé : {resume}")
    except Exception as e:
        log(f"⚠️  Résumé non généré : {e}")

    log("✅ PIPELINE TERMINÉ AVEC SUCCÈS")
    log("=" * 50)
    return True


if __name__ == "__main__":
    asyncio.run(run_pipeline())