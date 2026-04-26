import asyncio
from playwright.async_api import async_playwright
from datetime import date
import json, os

URL_BRVM        = "https://www.brvm.org/fr/cours-actions/0"
URL_SIKAFINANCE = "https://www.sikafinance.com/marches/aaz"


class BRVMScraper:

    async def get_cours_du_jour(self) -> list[dict]:
        resultats = await self._scrape_brvm()
        if not resultats:
            print("⚠️  BRVM.org vide → tentative SikaFinance...")
            resultats = await self._scrape_sikafinance()
        return resultats

    async def _scrape_brvm(self) -> list[dict]:
        print(f"🔄 Connexion à {URL_BRVM} ...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page    = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
            })
            try:
                await page.goto(URL_BRVM, timeout=40000, wait_until="networkidle")
                await page.wait_for_timeout(4000)
                print(f"   📄 Titre : {await page.title()}")

                rows = await page.query_selector_all("table tbody tr")
                print(f"   🔍 Lignes trouvées : {len(rows)}")

                # Dictionnaire : ticker → données (la dernière occurrence gagne)
                # La dernière occurrence = tableau principal complet
                par_ticker = {}

                for row in rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) < 2:
                        continue

                    textes = [
                        (await c.inner_text())
                        .strip()
                        .replace("\xa0", "")
                        .replace("\u202f", "")
                        for c in cells
                    ]

                    ticker = textes[0].strip()
                    if not ticker or ticker.startswith("BRVM") or not ticker[0].isalpha():
                        continue
                    if len(ticker) < 2:
                        continue

                    # Parse toutes les valeurs numériques de la ligne
                    numeriques = []
                    variation  = ""
                    for t in textes[1:]:
                        if "%" in t:
                            variation = t.strip()
                            continue
                        t_clean = t.replace(" ", "").replace(",", ".")
                        try:
                            val = float(t_clean)
                            if val > 0:
                                numeriques.append(val)
                        except:
                            pass

                    if not numeriques:
                        continue

                    # Le prix de clôture = premier nombre raisonnable (1 → 500 000 XOF)
                    cloture = None
                    for v in numeriques:
                        if 1 <= v <= 500_000:
                            cloture = v
                            break
                    if not cloture:
                        continue

                    # Cours veille = deuxième nombre raisonnable proche du cours
                    cours_veille = 0
                    for v in numeriques:
                        if v == cloture:
                            continue
                        # Veille doit être dans un écart de ±30% du cours actuel
                        if cloture * 0.70 <= v <= cloture * 1.30:
                            cours_veille = v
                            break

                    # Calcule variation si absente
                    if not variation and cours_veille > 0:
                        var_pct    = ((cloture - cours_veille) / cours_veille) * 100
                        variation  = f"{var_pct:+.2f}%"

                    # Volume = grand nombre qui n'est ni le cours ni la veille
                    volume = 0
                    for v in numeriques:
                        if v != cloture and v != cours_veille and v > 1000:
                            volume = int(v)
                            break

                    par_ticker[ticker] = {
                        "date":         str(date.today()),
                        "ticker":       ticker,
                        "cloture":      cloture,
                        "cours_veille": cours_veille,
                        "volume":       volume,
                        "variation":    variation,
                        "source":       "brvm.org",
                    }

                await browser.close()
                resultats = list(par_ticker.values())
                # Trie par ticker alphabétiquement
                resultats.sort(key=lambda x: x["ticker"])
                print(f"✅ {len(resultats)} actions récupérées depuis BRVM.org")
                return resultats

            except Exception as e:
                await browser.close()
                print(f"❌ Erreur BRVM.org : {e}")
                return []

    async def _scrape_sikafinance(self) -> list[dict]:
        print(f"🔄 Connexion à {URL_SIKAFINANCE} ...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page    = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
            })
            try:
                await page.goto(URL_SIKAFINANCE, timeout=40000, wait_until="networkidle")
                await page.wait_for_timeout(5000)

                rows = await page.query_selector_all("table tbody tr")
                if not rows:
                    rows = await page.query_selector_all("tr")

                resultats = []
                for row in rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) < 3:
                        continue
                    try:
                        textes = [(await c.inner_text()).strip().replace("\xa0","") for c in cells]
                        ticker = textes[0].split()[0] if textes[0] else ""
                        if not ticker or not ticker[0].isalpha() or len(ticker) < 2:
                            continue
                        prix = None
                        variation = "0%"
                        for t in textes[1:]:
                            t_clean = t.replace(" ","").replace(",",".")
                            try:
                                val = float(t_clean)
                                if prix is None and val > 1:
                                    prix = val
                            except:
                                if "%" in t:
                                    variation = t
                        if prix:
                            resultats.append({
                                "date":         str(date.today()),
                                "ticker":       ticker,
                                "cloture":      prix,
                                "cours_veille": 0,
                                "volume":       0,
                                "variation":    variation,
                                "source":       "sikafinance.com",
                            })
                    except Exception:
                        continue

                await browser.close()
                print(f"✅ {len(resultats)} actions depuis SikaFinance")
                return resultats

            except Exception as e:
                await browser.close()
                print(f"❌ Erreur SikaFinance : {e}")
                return []


async def main():
    scraper = BRVMScraper()
    cours   = await scraper.get_cours_du_jour()

    if cours:
        print(f"\n📊 COURS DU JOUR — BRVM ({cours[0]['date']})")
        print(f"{'TICKER':<14} {'CLÔTURE (XOF)':>14}  {'VEILLE':>12}  {'VARIATION':>10}  {'VOLUME':>10}")
        print("-" * 70)
        for a in cours:
            veille = f"{a['cours_veille']:>12,.0f}" if a['cours_veille'] else "           -"
            print(
                f"  {a['ticker']:<12} {a['cloture']:>14,.0f}  "
                f"{veille}  {a['variation']:>10}  {a['volume']:>10,}"
            )
        print(f"\n📈 Total : {len(cours)} actions | Source : {cours[0]['source']}")

        os.makedirs("../../data", exist_ok=True)
        with open("../../data/cours_test.json", "w", encoding="utf-8") as f:
            json.dump(cours, f, ensure_ascii=False, indent=2)
        print("💾 Sauvegardé dans data/cours_test.json")
    else:
        print(f"\n❌ Aucune donnée. Vérifie : {URL_BRVM}")


if __name__ == "__main__":
    asyncio.run(main())