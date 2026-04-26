from app.database import SessionLocal, CoursAction
from app.scrapers.brvm_scraper import BRVMScraper
from datetime import date
import asyncio


async def scrape_et_sauvegarder():
    """
    Récupère les cours du jour et les sauvegarde en base.
    Évite les doublons : si le cours du jour existe déjà, on skip.
    """
    scraper = BRVMScraper()
    cours   = await scraper.get_cours_du_jour()

    if not cours:
        print("❌ Aucune donnée à sauvegarder")
        return 0

    db      = SessionLocal()
    inseres = 0
    skips   = 0

    try:
        for c in cours:
            # Vérifie si ce cours existe déjà pour ce jour
            existe = db.query(CoursAction).filter(
                CoursAction.ticker == c["ticker"],
                CoursAction.date   == date.today()
            ).first()

            if existe:
                skips += 1
                continue

            enregistrement = CoursAction(
                date         = date.today(),
                ticker       = c["ticker"],
                cloture      = c["cloture"],
                cours_veille = c.get("cours_veille", 0),
                volume       = c.get("volume", 0),
                variation    = c.get("variation", ""),
                source       = c.get("source", "brvm.org"),
            )
            db.add(enregistrement)
            inseres += 1

        db.commit()
        print(f"✅ {inseres} actions sauvegardées | {skips} déjà existantes")
        return inseres

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur sauvegarde : {e}")
        return 0
    finally:
        db.close()


def lire_cours_du_jour():
    """Lit les cours du jour depuis la base."""
    db    = SessionLocal()
    cours = db.query(CoursAction).filter(
        CoursAction.date == date.today()
    ).order_by(CoursAction.ticker).all()
    db.close()
    return cours


if __name__ == "__main__":
    asyncio.run(scrape_et_sauvegarder())

    print("\n📊 Vérification en base :")
    print(f"{'TICKER':<14} {'CLÔTURE':>12}  {'VARIATION':>10}")
    print("-" * 42)
    for c in lire_cours_du_jour():
        print(f"  {c.ticker:<12} {c.cloture:>12,.0f}  {c.variation or '':>10}")