from dataclasses import dataclass
from app.database import SessionLocal, CoursAction, Recommandation
from app.scoring.explainer import generer_explication
from datetime import date
import statistics


@dataclass
class ResultatScore:
    ticker:          str
    signal:          str
    confiance:       int
    score_final:     float
    score_tendance:  float
    score_volume:    float
    score_momentum:  float
    explication:     str


class MoteurScoring:

    def scorer_tous(self) -> list[ResultatScore]:
        db      = SessionLocal()
        tickers = [r[0] for r in db.query(CoursAction.ticker).distinct().all()]
        db.close()

        print(f"   📋 {len(tickers)} tickers trouvés en base : {tickers[:5]}...")

        resultats = []
        for ticker in tickers:
            r = self.scorer_action(ticker)
            if r:
                resultats.append(r)
            else:
                print(f"   ⚠️  {ticker} ignoré (données insuffisantes)")

        resultats.sort(key=lambda x: x.score_final, reverse=True)
        return resultats

    def scorer_action(self, ticker: str) -> ResultatScore | None:
        db    = SessionLocal()
        cours = (
            db.query(CoursAction)
            .filter(CoursAction.ticker == ticker)
            .order_by(CoursAction.date.desc())
            .limit(30)
            .all()
        )
        db.close()

        if not cours:
            return None

        prix    = [c.cloture for c in cours if c.cloture and c.cloture > 0]
        volumes = [c.volume  for c in cours if c.volume is not None]

        if not prix:
            return None

        prix_actuel = prix[0]

        # ── Score tendance ──
        if len(prix) >= 2:
            prix_moyen   = statistics.mean(prix)
            tendance_pct = ((prix_actuel - prix_moyen) / prix_moyen) * 100
        else:
            tendance_pct = 0

        if tendance_pct > 5:
            score_tendance = 70
        elif tendance_pct > 0:
            score_tendance = 55
        elif tendance_pct > -5:
            score_tendance = 50
        else:
            score_tendance = 25

        # ── Score volume ──
        vol_actuel = volumes[0] if volumes else 0
        vol_moyen  = statistics.mean(volumes) if len(volumes) > 1 else vol_actuel

        if vol_moyen > 500_000:
            score_volume = 80
        elif vol_moyen > 100_000:
            score_volume = 65
        elif vol_moyen > 10_000:
            score_volume = 45
        elif vol_moyen > 1_000:
            score_volume = 30
        elif vol_moyen > 0:
            score_volume = 15
        else:
            score_volume = 5

        # ── Score momentum ──
        variation_str = cours[0].variation or "0%"
        try:
            var_pct = float(
                variation_str.replace("%", "").replace("+", "").replace(",", ".")
            )
        except:
            var_pct = 0

        if -2 <= var_pct <= 5:
            score_momentum = 65
        elif 5 < var_pct <= 7.5:
            score_momentum = 50
        elif var_pct > 7.5:
            score_momentum = 40
        elif var_pct < -10:
            score_momentum = 20
        else:
            score_momentum = 40

        # ── Score final ──
        score_final = (
            score_tendance * 0.40 +
            score_volume   * 0.40 +
            score_momentum * 0.20
        )

        # ── Signal ──
        if score_volume <= 5:
            signal    = "HOLD"
            confiance = 15
        elif score_final >= 62:
            signal    = "BUY"
            confiance = min(int(score_final), 82)
        elif score_final >= 42:
            signal    = "HOLD"
            confiance = int(score_final)
        else:
            signal    = "SELL"
            confiance = min(int(100 - score_final), 75)

        # ── Explication Groq ──
        explication = generer_explication(
            ticker         = ticker,
            signal         = signal,
            confiance      = confiance,
            score_final    = score_final,
            score_volume   = score_volume,
            score_tendance = score_tendance,
            variation      = cours[0].variation or "",
            prix           = prix_actuel,
        )

        return ResultatScore(
            ticker         = ticker,
            signal         = signal,
            confiance      = confiance,
            score_final    = round(score_final, 1),
            score_tendance = score_tendance,
            score_volume   = score_volume,
            score_momentum = score_momentum,
            explication    = explication,
        )

    def sauvegarder_recommandations(self, resultats: list[ResultatScore]):
        db = SessionLocal()
        try:
            for r in resultats:
                db.query(Recommandation).filter(
                    Recommandation.ticker == r.ticker,
                    Recommandation.date   == date.today()
                ).delete()

                db.add(Recommandation(
                    date        = date.today(),
                    ticker      = r.ticker,
                    signal      = r.signal,
                    confiance   = r.confiance,
                    score_final = r.score_final,
                    explication = r.explication,
                ))
            db.commit()
            print(f"✅ {len(resultats)} recommandations sauvegardées")
        except Exception as e:
            db.rollback()
            print(f"❌ Erreur : {e}")
        finally:
            db.close()


if __name__ == "__main__":
    moteur    = MoteurScoring()
    resultats = moteur.scorer_tous()

    buy  = [r for r in resultats if r.signal == "BUY"]
    hold = [r for r in resultats if r.signal == "HOLD"]
    sell = [r for r in resultats if r.signal == "SELL"]

    print(f"\n🤖 RECOMMANDATIONS DU JOUR — {date.today()}")
    print(f"{'TICKER':<12} {'SIGNAL':<6} {'CONFIANCE':>10} {'SCORE':>7}")
    print("-" * 45)

    print("\n✅ ACHETER :")
    for r in buy:
        print(f"  {r.ticker:<12} {r.signal:<6} {r.confiance:>8}%  {r.score_final:>6}")
        print(f"     → {r.explication[:100]}")

    print("\n⏸️  CONSERVER :")
    for r in hold[:5]:
        print(f"  {r.ticker:<12} {r.signal:<6} {r.confiance:>8}%  {r.score_final:>6}")

    print("\n🔴 VENDRE :")
    for r in sell:
        print(f"  {r.ticker:<12} {r.signal:<6} {r.confiance:>8}%  {r.score_final:>6}")
        print(f"     → {r.explication[:100]}")

    print(f"\n📊 Résumé : {len(buy)} BUY | {len(hold)} HOLD | {len(sell)} SELL")
    moteur.sauvegarder_recommandations(resultats)