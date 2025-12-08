import streamlit as st
import openai
from serpapi import GoogleSearch
import resend

# --- CONFIGURATION ---
st.set_page_config(page_title="LocalHunter - MVP", page_icon="🎯", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #4F46E5; color: white; border-radius: 8px; border: none; }
    div.stButton > button:hover { background-color: #4338CA; color: white; }
</style>
""", unsafe_allow_html=True)

# --- SECRETS ---
try:
    openai.api_key = st.secrets["OPENAI_KEY"]
    serpapi_key = st.secrets["SERPAPI_KEY"]
    resend.api_key = st.secrets["RESEND_KEY"]
    api_ready = True
except:
    st.warning("⚠️ Clés API manquantes dans les Secrets Streamlit.")
    api_ready = False

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎯 LocalHunter")
    if api_ready:
        st.success("✅ Système connecté")
    else:
        st.error("🔴 Déconnecté")

# --- FONCTIONS ---
def search_google_maps(job, city, api_key):
    try:
        params = { "engine": "google_maps", "q": f"{job} {city}", "type": "search", "api_key": api_key }
        search = GoogleSearch(params)
        return search.get_dict().get("local_results", [])
    except:
        return []

def generate_website_code(business_name, activity, city, address, phone):
    prompt = f"Crée un site One-Page HTML moderne avec TailwindCSS pour '{business_name}', {activity} à {city}. Adresse: {address}, Tel: {phone}. Code complet dans une seule balise <html>."
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except:
        return "<h1>Erreur de génération</h1>"

# --- INTERFACE ---
st.title("Chasseur de Prospects & Générateur Web")

col1, col2 = st.columns(2)
with col1: job_input = st.text_input("Activité", "Boulanger")
with col2: city_input = st.text_input("Ville", "Paris")

if 'prospects' not in st.session_state: st.session_state.prospects = []

if st.button("🚀 Lancer la recherche", disabled=not api_ready):
    with st.status("Recherche en cours..."):
        raw = search_google_maps(job_input, city_input, serpapi_key)
        clean = [r for r in raw if "website" not in r]
        st.session_state.prospects = clean

if st.session_state.prospects:
    st.success(f"{len(st.session_state.prospects)} prospects sans site trouvés !")
    for p in st.session_state.prospects:
        with st.expander(f"📍 {p.get('title')}"):
            if st.button(f"Générer Site", key=p.get('place_id')):
                with st.spinner("Génération..."):
                    code = generate_website_code(p.get('title'), job_input, city_input, p.get('address'), p.get('phone', ''))
                    st.code(code, language='html')