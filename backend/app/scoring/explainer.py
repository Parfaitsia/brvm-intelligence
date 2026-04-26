import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MODEL = "llama-3.3-70b-versatile"

def _get_client():
    """Crée le client Groq à la demande (pas au démarrage)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY non définie")
    return Groq(api_key=api_key)


def generer_explication(ticker, signal, confiance, score_final,
                        score_volume, score_tendance, variation, prix):
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
Tu es un conseiller financier pédagogue spécialisé sur la BRVM.
Voici les données d'analyse pour une action :
{contexte}
Génère une explication courte (3 phrases maximum) pour un débutant complet.
- Utilise un langage simple, pas de jargon
- Explique POURQUOI ce signal (BUY/HOLD/SELL)
- Termine TOUJOURS par : "⚠️ Pas un conseil financier officiel."
- Réponds uniquement en français
"""
    try:
        client = _get_client()
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


def generer_resume_marche(nb_buy, nb_hold, nb_sell, top_buy, top_sell):
    top_buy_str  = ", ".join(top_buy[:3])  if top_buy  else "aucune"
    top_sell_str = ", ".join(top_sell[:3]) if top_sell else "aucune"
    prompt = f"""
Tu es un journaliste financier spécialisé sur la BRVM en Afrique de l'Ouest.
Résumé du marché aujourd'hui :
- Actions avec signal ACHAT : {nb_buy}
- Actions avec signal CONSERVER : {nb_hold}
- Actions avec signal VENDRE : {nb_sell}
- Meilleures opportunités : {top_buy_str}
- Actions à surveiller : {top_sell_str}
Génère un résumé en 3-4 phrases simples pour un débutant.
Réponds uniquement en français.
"""
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        sentiment = "haussier" if nb_buy > nb_sell else "baissier" if nb_sell > nb_buy else "neutre"
        return f"Le marché BRVM est {sentiment} aujourd'hui. ⚠️ Pas un conseil financier officiel."


def repondre_question(question, contexte_marche):
    prompt = f"""
Tu es un assistant pédagogue spécialisé sur la BRVM.
Contexte : {contexte_marche.get('nb_actions', 47)} actions suivies,
{contexte_marche.get('nb_buy', 0)} signaux achat, {contexte_marche.get('nb_sell', 0)} signaux vente.
Question : "{question}"
Réponds en 2-3 phrases simples en français.
"""
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Désolé, je ne peux pas répondre pour le moment. Réessaie dans quelques instants."


def _explication_fallback(ticker, signal, score_volume):
    if signal == "BUY":
        return f"✅ {ticker} montre des signaux encourageants. ⚠️ Pas un conseil financier officiel."
    elif signal == "SELL":
        raison = "la liquidité est faible" if score_volume < 30 else "la tendance est baissière"
        return f"🔴 {ticker} : {raison}. ⚠️ Pas un conseil financier officiel."
    else:
        return f"⏸️ {ticker} : situation neutre, observez encore. ⚠️ Pas un conseil financier officiel."