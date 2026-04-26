import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MODEL = "llama-3.3-70b-versatile"


def _get_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def generer_explication(ticker, signal, confiance, score_final,
                        score_volume, score_tendance, variation, prix):
    prompt = f"""
Tu es un conseiller financier pédagogue spécialisé sur la BRVM.
Action : {ticker} | Signal : {signal} | Confiance : {confiance}%
Score : {score_final}/100 | Liquidité : {score_volume}/100
Variation : {variation or "inconnue"} | Prix : {prix:,.0f} XOF
Génère une explication de 3 phrases maximum pour un débutant.
Langage simple, explique le signal, termine par "⚠️ Pas un conseil financier officiel."
Réponds en français uniquement.
"""
    try:
        response = _get_client().chat.completions.create(
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
    prompt = f"""
Tu es un journaliste financier spécialisé sur la BRVM.
Marché aujourd'hui : {nb_buy} achats, {nb_hold} conservation, {nb_sell} ventes.
Opportunités : {", ".join(top_buy[:3]) if top_buy else "aucune"}
Résumé en 3-4 phrases simples pour débutant. En français.
"""
    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        sentiment = "haussier" if nb_buy > nb_sell else "baissier"
        return f"Le marché BRVM est {sentiment} aujourd'hui. ⚠️ Pas un conseil financier officiel."


def repondre_question(question, contexte_marche):
    prompt = f"""
Tu es un assistant pédagogue spécialisé sur la BRVM.
{contexte_marche.get('nb_actions', 47)} actions suivies.
Question : "{question}"
Réponds en 2-3 phrases simples en français.
"""
    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Désolé, je ne peux pas répondre pour le moment."


def _explication_fallback(ticker, signal, score_volume):
    if signal == "BUY":
        return f"✅ {ticker} montre des signaux encourageants. ⚠️ Pas un conseil financier officiel."
    elif signal == "SELL":
        raison = "la liquidité est faible" if score_volume < 30 else "la tendance est baissière"
        return f"🔴 {ticker} : {raison}. ⚠️ Pas un conseil financier officiel."
    return f"⏸️ {ticker} : situation neutre, observez encore. ⚠️ Pas un conseil financier officiel."