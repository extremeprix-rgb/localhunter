import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time
import re

st.set_page_config(page_title="LocalHunter V8 (Clean)", page_icon="🏢", layout="wide")

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

# --- FONCTION DE NETTOYAGE (LA CISAILLE) ---
def clean_html_output(raw_text):
    """Garde uniquement ce qu'il y a entre <!DOCTYPE html> et </html>"""
    # 1. Enlever les balises markdown
    text = raw_text.replace("```html", "").replace("```", "").strip()
    
    # 2. Trouver le début et la fin
    start_marker = "<!DOCTYPE html>"
    end_marker = "</html>"
    
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)
    
    # 3. Couper proprement
    if start_idx != -1 and end_idx != -1:
        # On garde du début du DOCTYPE jusqu'à la fin du </html>
        return text[start_idx : end_idx + len(end_marker)]
    
    # Si on ne trouve pas les balises (rare), on renvoie le texte nettoyé du markdown
    return text

# --- MOTEUR DE RECHERCHE (V7 Logic) ---
def smart_search(job, city, api_key, max_pages):
    all_results = []
    seen = set()
    status_box = st.empty()
    
    status_box.info(f"📍 Scan initial de {city}...")
    
    try:
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
        
        results = data.get("local_results", [])
        for res in results:
            pid = res.get("place_id")
            if pid and pid not in seen:
                all_results.append(res)
                seen.add(pid)

        # Tentative Pagination
        ll_token = None
        try:
            metadata = data.get("search_metadata", {})
            url = metadata.get("google_maps_url", "")
            match = re.search(r'@([-0-9.]+),([-0-9.]+),([0-9.]+)z', url)
            if match:
                ll_token = f"@{match.group(1)},{match.group(2)},{match.group(3)}z"
        except: pass

        if ll_token and max_pages > 1:
            for page in range(1, max_pages):
                status_box.info(f"🔄 Extension du scan (Page {page+1})...")
                try:
                    params["start"] = page * 20
                    params["ll"] = ll_token
                    sub_search = GoogleSearch(params)
                    sub_results = sub_search.get_dict().get("local_results", [])
                    if not sub_results: break
                    for res in sub_results:
                        pid = res.get("place_id")
                        if pid and pid not in seen:
                            all_results.append(res)
                            seen.add(pid)
                    time.sleep(1)
                except: break
        
    except Exception as e:
        st.error(f"Erreur de recherche : {e}")

    status_box.success(f"✅ Terminé : {len(all_results)} entreprises analysées.")
    time.sleep(2)
    status_box.empty()
    return all_results

# --- GENERATEURS ---
def generate_code(name, job, city, addr, tel):
    prompt = f"Code HTML One-Page (TailwindCSS) pour {name} ({job}) à {city}. Adresse: {addr}, Tel: {tel}. Commence par <!DOCTYPE html>."
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        # On passe le résultat dans la cisaille
        return clean_html_output(resp.choices[0].message.content)
    except: return "<!-- Erreur Gen -->"

def modify_code(html, ins):
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Modifie ce HTML: {ins}. Renvoie tout le code HTML complet."}])
        # On passe le résultat dans la cisaille
        return clean_html_output(resp.choices[0].message.content)
    except: return html

def generate_email(name):
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Email prospection court AIDA pour {name}."}])
        return resp.choices[0].message.content
    except: return "Erreur Email"

# --- INTERFACE ---
st.title("LocalHunter V8 (Clean Output)")

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
        raw = smart_search(job, city, serpapi_key, pages)
        clean = [r for r in raw if "website" not in r]
        st.session_state.prospects = clean
        st.session_state.stats = (len(raw), len(clean))

    if 'prospects' in st.session_state:
        if 'stats' in st.session_state:
            tot, kep = st.session_state.stats
            st.info(f"📊 {tot} analysés → {kep} sans site.")
            
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
                        st.text("👇 Code HTML propre (Copiable)")
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
