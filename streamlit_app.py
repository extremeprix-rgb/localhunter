import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time

st.set_page_config(page_title="LocalHunter V6 (Deep Scan)", page_icon="🏢", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #000000; color: white; border-radius: 6px; font-weight: 600; }
    .stat-card { background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; text-align: center; }
    .stat-val { font-size: 24px; font-weight: bold; color: #0f172a; }
    .stat-lbl { font-size: 12px; color: #64748b; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# Secrets
try:
    api_key = st.secrets.get("MISTRAL_KEY", st.secrets.get("OPENAI_KEY"))
    serpapi_key = st.secrets["SERPAPI_KEY"]
    client = openai.OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
except: st.error("Clés manquantes"); st.stop()

# --- ENGINE ---
def deep_search_google_maps(job, city, api_key, max_pages=3):
    """Scanne plusieurs pages de résultats (Pagination)"""
    all_results = []
    seen_ids = set() # Pour éviter les doublons
    
    # Barre de progression dans l'UI
    progress_text = "Démarrage du Deep Scan..."
    my_bar = st.progress(0, text=progress_text)
    
    for page in range(max_pages):
        start_index = page * 20
        pct = int((page / max_pages) * 100)
        my_bar.progress(pct, text=f"Scan page {page+1}/{max_pages} (Résultats {start_index}-{start_index+20})...")
        
        try:
            params = {
                "engine": "google_maps",
                "q": f"{job} {city}",
                "type": "search",
                "google_domain": "google.fr",
                "hl": "fr",
                "num": 20, # Max par page
                "start": start_index, # Pagination
                "api_key": api_key
            }
            search = GoogleSearch(params)
            results = search.get_dict().get("local_results", [])
            
            if not results:
                break # Plus de résultats, on arrête
                
            for res in results:
                pid = res.get("place_id")
                if pid not in seen_ids:
                    all_results.append(res)
                    seen_ids.add(pid)
            
            # Pause respectueuse pour l'API (évite le blocage)
            time.sleep(0.5)
            
        except Exception as e:
            st.error(f"Erreur Page {page}: {e}")
            break
            
    my_bar.progress(100, text="Scan terminé !")
    time.sleep(0.5)
    my_bar.empty()
    
    return all_results

def generate_website_code(business_name, activity, city, address, phone):
    prompt = f"Crée site One-Page HTML (TailwindCSS) pour {business_name} ({activity}) à {city}. Adresse: {address}, Tel: {phone}. Structure: Navbar, Hero, Services, Contact. Code HTML STRICTEMENT SEUL, commence par <!DOCTYPE html>."
    try:
        response = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except: return "<!-- Erreur IA -->"

def modify_website_code(current_html, instructions):
    prompt = f"Modifie ce HTML selon: '{instructions}'. Renvoie UNIQUEMENT le code HTML complet."
    try:
        response = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except: return current_html

def generate_sales_email(business_name):
    prompt = f"Email prospection court AIDA pour vendre site web à {business_name}."
    try:
        response = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content
    except: return "Erreur"

# --- UI ---
st.title("LocalHunter V6 (Deep Scan)")

tab1, tab2 = st.tabs(["CHASSE MASSIVE", "ATELIER"])

with tab1:
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1: job = st.text_input("Activité", "Maçon")
    with c2: city = st.text_input("Ville", "Lyon")
    with c3: pages = st.number_input("Pages à scanner", 1, 5, 3, help="1 page = 20 résultats")
    with c4: 
        st.write("")
        st.write("")
        btn = st.button("🚀 SCAN", use_container_width=True)

    if btn:
        raw = deep_search_google_maps(job, city, serpapi_key, max_pages=pages)
        clean = [r for r in raw if "website" not in r]
        
        st.session_state.prospects = clean
        st.session_state.stats = (len(raw), len(raw)-len(clean), len(clean))

    if 'stats' in st.session_state:
        tot, rej, kep = st.session_state.stats
        k1, k2, k3 = st.columns(3)
        k1.markdown(f"<div class='stat-card'><div class='stat-val'>{tot}</div><div class='stat-lbl'>Profils Analysés</div></div>", unsafe_allow_html=True)
        k2.markdown(f"<div class='stat-card'><div class='stat-val' style='color:orange'>{rej}</div><div class='stat-lbl'>Déjà Numérisés</div></div>", unsafe_allow_html=True)
        k3.markdown(f"<div class='stat-card'><div class='stat-val' style='color:green'>{kep}</div><div class='stat-lbl'>Prospects Cibles</div></div>", unsafe_allow_html=True)
        st.divider()

    if 'prospects' in st.session_state:
        for p in st.session_state.prospects:
            with st.expander(f"📍 {p.get('title')} ({p.get('address')})"):
                ac, vi = st.columns([1, 2])
                pid = p.get('place_id')
                
                with ac:
                    if st.button("⚡ Générer Site", key=f"g_{pid}"):
                        st.session_state[f"h_{pid}"] = generate_website_code(p.get('title'), job, city, p.get('address'), p.get('phone'))
                    if st.button("📧 Email", key=f"m_{pid}"):
                        st.session_state[f"e_{pid}"] = generate_sales_email(p.get('title'))
                
                with vi:
                    if f"h_{pid}" in st.session_state:
                        st.code(st.session_state[f"h_{pid}"], language="html")
                        with st.expander("Voir"): st.components.v1.html(st.session_state[f"h_{pid}"], height=300, scrolling=True)
                    if f"e_{pid}" in st.session_state:
                        st.text_area("Mail", st.session_state[f"e_{pid}"])

with tab2:
    up = st.file_uploader("HTML", type=['html'])
    if up:
        h = up.getvalue().decode("utf-8")
        st.components.v1.html(h, height=300, scrolling=True)
        ins = st.text_input("Modif")
        if st.button("Appliquer"):
            st.session_state['new'] = modify_website_code(h, ins)
            st.rerun()
    if 'new' in st.session_state: st.code(st.session_state['new'], language="html")
