import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time
import re

st.set_page_config(page_title="LocalHunter V7 (Stable)", page_icon="🏢", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #000000; color: white; border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Secrets
try:
    api_key = st.secrets.get("MISTRAL_KEY", st.secrets.get("OPENAI_KEY"))
    serpapi_key = st.secrets["SERPAPI_KEY"]
    client = openai.OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
except:
    st.error("⚠️ Clés API manquantes.")
    st.stop()

# --- MOTEUR DE RECHERCHE INTELLIGENT ---
def smart_search(job, city, api_key, max_pages):
    all_results = []
    seen = set()
    status_box = st.empty()
    
    # 1. PAGE 1 (Garanti sans erreur)
    status_box.info(f"📍 Scan initial de {city}...")
    
    try:
        # Pas de paramètre 'start' ici, donc pas d'erreur 'Missing location'
        params = {
            "engine": "google_maps",
            "q": f"{job} {city}",
            "type": "search",
            "google_domain": "google.fr",
            "hl": "fr",
            "num": 20,
            "api_key": api_key
        }
        search = GoogleSearch(params)
        data = search.get_dict()
        
        # Récupération résultats P1
        results = data.get("local_results", [])
        for res in results:
            pid = res.get("place_id")
            if pid and pid not in seen:
                all_results.append(res)
                seen.add(pid)

        # 2. TENTATIVE DE PAGINATION (Si possible)
        # On essaie d'extraire le paramètre @lat,lon,zoom de l'URL fournie par Google
        ll_token = None
        try:
            metadata = data.get("search_metadata", {})
            url = metadata.get("google_maps_url", "")
            # Regex pour trouver @12.345,67.890,14z
            match = re.search(r'@([-0-9.]+),([-0-9.]+),([0-9.]+)z', url)
            if match:
                ll_token = f"@{match.group(1)},{match.group(2)},{match.group(3)}z"
        except:
            pass

        # Si on a trouvé le token magique, on continue
        if ll_token and max_pages > 1:
            for page in range(1, max_pages):
                status_box.info(f"🔄 Extension du scan (Page {page+1})...")
                try:
                    params["start"] = page * 20
                    params["ll"] = ll_token # Le sésame pour la pagination !
                    
                    sub_search = GoogleSearch(params)
                    sub_data = sub_search.get_dict()
                    sub_results = sub_data.get("local_results", [])
                    
                    if not sub_results: break
                    
                    for res in sub_results:
                        pid = res.get("place_id")
                        if pid and pid not in seen:
                            all_results.append(res)
                            seen.add(pid)
                    time.sleep(1) # Pause API
                except:
                    break # On arrête silencieusement si la pagination plante
        
    except Exception as e:
        st.error(f"Erreur de recherche : {e}")

    status_box.success(f"✅ Terminé : {len(all_results)} entreprises analysées.")
    time.sleep(2)
    status_box.empty()
    return all_results

def generate_code(name, job, city, addr, tel):
    prompt = f"Code HTML One-Page (TailwindCSS) pour {name} ({job}) à {city}. Adresse: {addr}, Tel: {tel}. Commence par <!DOCTYPE html>."
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return resp.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except: return "<!-- Erreur Gen -->"

def generate_email(name):
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Email prospection court AIDA pour {name}."}])
        return resp.choices[0].message.content
    except: return "Erreur Email"

def modify_code(html, ins):
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Modifie ce HTML: {ins}. Renvoie tout le code HTML."}])
        return resp.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except: return html

# --- INTERFACE ---
st.title("LocalHunter V7 (Stable)")

tab1, tab2 = st.tabs(["CHASSE", "ATELIER"])

with tab1:
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1: job = st.text_input("Activité", "Maçon")
    with c2: city = st.text_input("Ville", "Bordeaux")
    with c3: pages = st.number_input("Pages", 1, 5, 2)
    with c4: 
        st.write("")
        st.write("")
        launch = st.button("SCAN", use_container_width=True)

    if launch:
        st.session_state.prospects = []
        # On utilise la recherche intelligente qui ne plante pas
        raw = smart_search(job, city, serpapi_key, pages)
        
        # Filtrage strict
        clean = [r for r in raw if "website" not in r]
        
        st.session_state.prospects = clean
        st.session_state.stats = (len(raw), len(clean))

    if 'prospects' in st.session_state:
        if 'stats' in st.session_state:
            tot, kep = st.session_state.stats
            st.info(f"📊 {tot} analysés → {kep} sans site.")
            
            if tot > 0 and kep == 0:
                st.warning("Tout le monde a un site ici ! Changez de ville ou de métier.")

        for p in st.session_state.prospects:
            with st.expander(f"📍 {p.get('title')} ({p.get('address')})"):
                c_a, c_b = st.columns([1, 2])
                pid = p.get('place_id')
                
                with c_a:
                    if st.button("⚡ Site", key=f"g_{pid}"):
                        st.session_state[f"h_{pid}"] = generate_code(p.get('title'), job, city, p.get('address'), p.get('phone'))
                    if st.button("📧 Email", key=f"m_{pid}"):
                        st.session_state[f"e_{pid}"] = generate_email(p.get('title'))
                
                with c_b:
                    if f"h_{pid}" in st.session_state:
                        st.text("👇 Copiez le code (Bouton en haut à droite)")
                        st.code(st.session_state[f"h_{pid}"], language="html")
                        with st.expander("Voir"): st.components.v1.html(st.session_state[f"h_{pid}"], height=300, scrolling=True)
                    if f"e_{pid}" in st.session_state:
                        st.text_area("Mail", st.session_state[f"e_{pid}"])

with tab2:
    up = st.file_uploader("Modifier HTML", type=['html'])
    if up:
        h = up.getvalue().decode("utf-8")
        st.components.v1.html(h, height=200, scrolling=True)
        ins = st.text_input("Modif:")
        if st.button("Appliquer"):
            st.session_state['new'] = modify_code(h, ins)
            st.rerun()
    if 'new' in st.session_state: st.code(st.session_state['new'], language="html")
