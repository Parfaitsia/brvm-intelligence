import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

cle = os.getenv("GROQ_API_KEY")
print(f"🔑 Clé trouvée : {cle[:10]}..." if cle else "❌ Clé GROQ_API_KEY non trouvée dans .env")

try:
    client = Groq(api_key=cle)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # ✅ nouveau modèle
        messages=[{"role": "user", "content": "Dis bonjour en français en une phrase."}],
        max_tokens=50,
    )
    print(f"✅ Groq répond : {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ Erreur Groq : {e}")