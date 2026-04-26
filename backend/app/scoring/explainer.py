import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"   # ✅ modèle actuel Groq


def generer_explication(ticker: str, signal: str, confiance: int,
                         score_final: float, score_volume: float,
                         score_tendance: float, variation: str,
                         prix: float) -> str:
    contexte = f"""
Action : {ticker}
Signal : {signal}
Confiance : {confiance}%
Score global : {score_final}/100
Score liquidité : {score_volume}/100 ({"faible" if score_volume < 30 else "correct" if score_volume < 60 else "bon"})
Score tendance : {score_tendance}/100
Variation du jour : {variation or "inconnue"}
Prix actuel : {prix:,.0f} XOF
"""

    prompt = f"""
Tu es un conseiller financier pédagogue spécialisé sur la BRVM (Bourse Régionale des Valeurs Mobilières d'Afrique de l'Ouest).

Voici les données d'analyse pour une action :
{contexte}

Génère une explication courte (3 phrases maximum) pour un débutant complet qui ne connaît pas la finance.
- Utilise un langage simple, pas de jargon
- Explique POURQUOI ce signal (BUY/HOLD/SELL)
- Mentionne le risque principal si pertinent
- Termine TOUJOURS par : "⚠️ Pas un conseil financier officiel."
- Réponds uniquement en français
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"   ⚠️  Groq erreur pour {ticker} : {e}")
        return _explication_fallback(ticker, signal, score_volume)


def generer_resume_marche(nb_buy: int, nb_hold: int, nb_sell: int,
                           top_buy: list, top_sell: list) -> str:
    top_buy_str  = ", ".join(top_buy[:3])  if top_buy  else "aucune"
    top_sell_str = ", ".join(top_sell[:3]) if top_sell else "aucune"

    prompt = f"""
Tu es un journaliste financier spécialisé sur la BRVM en Afrique de l'Ouest.

Résumé du marché aujourd'hui :
- Actions avec signal ACHAT : {nb_buy}
- Actions avec signal CONSERVER : {nb_hold}
- Actions avec signal VENDRE : {nb_sell}
- Meilleures opportunités détectées : {top_buy_str}
- Actions à surveiller : {top_sell_str}

Génère un résumé du marché en 3-4 phrases simples pour un investisseur débutant.
- Décris l'ambiance générale du marché (haussier/baissier/neutre)
- Donne un conseil pratique général
- Rappelle l'importance de la prudence
- Réponds uniquement en français, style journal accessible
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        sentiment = "haussier" if nb_buy > nb_sell else "baissier" if nb_sell > nb_buy else "neutre"
        return (
            f"Le marché BRVM est {sentiment} aujourd'hui avec "
            f"{nb_buy} signaux d'achat et {nb_sell} signaux de vente. "
            f"⚠️ Pas un conseil financier officiel."
        )


def repondre_question(question: str, contexte_marche: dict) -> str:
    prompt = f"""
Tu es un assistant pédagogue spécialisé sur la BRVM (Bourse d'Afrique de l'Ouest).
Tu réponds aux questions de débutants sur la finance et le marché boursier.

Contexte du marché aujourd'hui :
- Nombre d'actions suivies : {contexte_marche.get('nb_actions', 47)}
- Signaux achat : {contexte_marche.get('nb_buy', 0)}
- Signaux vente : {contexte_marche.get('nb_sell', 0)}

Question du débutant : "{question}"

Réponds en 2-3 phrases simples, sans jargon, en français.
Si la question porte sur une action spécifique que tu ne connais pas, dis-le honnêtement.
Termine par un rappel que tu n'es pas un conseiller financier officiel si la question concerne un investissement.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return "Désolé, je ne peux pas répondre pour le moment. Réessaie dans quelques instants."


def _explication_fallback(ticker: str, signal: str, score_volume: float) -> str:
    if signal == "BUY":
        return f"✅ {ticker} montre des signaux encourageants. ⚠️ Pas un conseil financier officiel."
    elif signal == "SELL":
        raison = "la liquidité est faible" if score_volume < 30 else "la tendance est baissière"
        return f"🔴 {ticker} : {raison}. ⚠️ Pas un conseil financier officiel."
    else:
        return f"⏸️ {ticker} : situation neutre, observez encore quelques séances. ⚠️ Pas un conseil financier officiel."