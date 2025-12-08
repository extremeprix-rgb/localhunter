import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time

st.set_page_config(page_title="LocalHunter V6.1", page_icon="🛠️", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #000000; color: white; border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Secrets & Config
try:
    api_key = st.secrets.get("MISTRAL_KEY", st.secrets.get("OPENAI_KEY"))
    serpapi_key = st.secrets["SERPAPI_KEY"]
    client = openai.OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
except:
    st.error("⚠️ Clés API manquantes. Vérifiez les Secrets.")
    st.stop()

# --- MOTEUR DE RECHERCHE ---
def robust_search(job, city, api_key, max_pages):
    all_results = []
    seen = set()
    
    status_box = st.empty() # Zone de texte dynamique
    
    for page in range(max_pages):
        start = page * 20
        status_box.info(f"🔄 Scan Page {page+1}/{max_pages} (Position {start})...")
        
        try:
            params = {
                "engine": "google_maps",
                "q": f"{job} {city}",
                "type": "search",
                "google_domain": "google.fr",
                "hl": "fr",
                "num": 20,
                "start": start,
                "api_key": api_key
            }
            
            search = GoogleSearch(params)
            data = search.get_dict()
            
            # DIAGNOSTIC : Vérifier si l'API renvoie une erreur
            if "error" in data:
                st.error(f"❌ Erreur SerpApi : {data['error']}")
                break
                
            results = data.get("local_results", [])
            
            if not results:
                st.warning(f"⚠️ Page {page+1} vide. Arrêt du scan.")
                break
                
            for res in results:
                pid = res.get("place_id")
                if pid not in seen:
                    all_results.append(res)
                    seen.add(pid)
            
            # Pause de sécurité (1 seconde) pour ne pas se faire bloquer
            time.sleep(1)
            
        except Exception as e:
            st.error(f"❌ Crash technique : {e}")
            break
            
    status_box.success(f"✅ Terminé : {len(all_results)} résultats trouvés au total.")
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
st.title("LocalHunter V6.1 (Debug Mode)")

tab1, tab2 = st.tabs(["CHASSE", "ATELIER"])

with tab1:
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1: job = st.text_input("Activité", "Plombier")
    with c2: city = st.text_input("Ville", "Paris")
    with c3: pages = st.number_input("Pages", 1, 5, 2)
    with c4: 
        st.write("")
        st.write("")
        launch = st.button("SCAN", use_container_width=True)

    if launch:
        st.session_state.prospects = [] # Reset
        raw = robust_search(job, city, serpapi_key, pages)
        
        # Filtrage
        clean = [r for r in raw if "website" not in r]
        st.session_state.prospects = clean
        st.session_state.stats = (len(raw), len(clean))

    if 'prospects' in st.session_state:
        if 'stats' in st.session_state:
            tot, kep = st.session_state.stats
            st.info(f"📊 Rapport : {tot} analysés → {kep} sans site web.")
        
        if len(st.session_state.prospects) == 0 and 'stats' in st.session_state:
            st.warning("Aucun prospect qualifié trouvé. Essayez une autre ville ou activité.")

        for p in st.session_state.prospects:
            with st.expander(f"📍 {p.get('title', '?')} ({p.get('address', '?')})"):
                c_a, c_b = st.columns([1, 2])
                pid = p.get('place_id')
                
                with c_a:
                    if st.button("⚡ Site", key=f"g_{pid}"):
                        st.session_state[f"h_{pid}"] = generate_code(p.get('title'), job, city, p.get('address'), p.get('phone'))
                    if st.button("📧 Email", key=f"m_{pid}"):
                        st.session_state[f"e_{pid}"] = generate_email(p.get('title'))
                
                with c_b:
                    if f"h_{pid}" in st.session_state:
                        st.code(st.session_state[f"h_{pid}"], language="html")
                        with st.expander("Voir"): st.components.v1.html(st.session_state[f"h_{pid}"], height=300, scrolling=True)
                    if f"e_{pid}" in st.session_state:
                        st.text_area("Mail", st.session_state[f"e_{pid}"], height=150)

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
