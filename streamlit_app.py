import streamlit as st
import openai
from serpapi import GoogleSearch
import resend

st.set_page_config(page_title="LocalHunter V4.1", page_icon="🏢", layout="wide")

# CSS Style
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #0f172a; color: white; border-radius: 8px; border: none; font-weight: bold; }
    div.stButton > button:hover { background-color: #334155; color: white; }
</style>
""", unsafe_allow_html=True)

# Secrets
try:
    api_key = st.secrets.get("MISTRAL_KEY", st.secrets.get("OPENAI_KEY"))
    serpapi_key = st.secrets["SERPAPI_KEY"]
    
    client = openai.OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
except Exception as e:
    st.error(f"⚠️ Erreur Config: {e}")
    st.stop()

# Fonctions
def search_google_maps(job, city, api_key):
    try:
        params = {"engine": "google_maps", "q": f"{job} {city}", "type": "search", "google_domain": "google.fr", "hl": "fr", "num": 20, "api_key": api_key}
        search = GoogleSearch(params)
        return search.get_dict().get("local_results", [])
    except: return []

def generate_website_code(business_name, activity, city, address, phone):
    prompt = f"Tu es dév web. Crée un site One-Page HTML complet (TailwindCSS) pour {business_name} ({activity}) à {city}. Adresse: {address}, Tel: {phone}. Structure: Navbar, Hero, Services, Contact. Code HTML UNIQUEMENT."
    try:
        response = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except Exception as e: return f"<h1>Erreur IA: {e}</h1>"

def modify_website_code(current_html, instructions):
    prompt = f"Tu es expert maintenance. Code HTML actuel:\n{current_html[:2000]}...\nInstruction modif: {instructions}\nRenvoie tout le HTML corrigé."
    try:
        response = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except Exception as e: return f"Erreur: {e}"

def generate_sales_email(business_name):
    prompt = f"Email de prospection court pour {business_name} pour lui vendre un site démo déjà fait. Méthode AIDA."
    try:
        response = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content
    except: return "Erreur email"

# Interface
st.title("🚀 LocalHunter - Suite Complète")
tab_hunter, tab_editor = st.tabs(["🔫 Mode Chasseur", "🔧 Atelier de Retouche"])

# --- MODE CHASSEUR ---
with tab_hunter:
    c1, c2 = st.columns(2)
    with c1: job = st.text_input("Activité", "Coiffeur")
    with c2: city = st.text_input("Ville", "Bordeaux")
    
    if st.button("🔎 Scanner"):
        with st.status("Recherche..."):
            raw = search_google_maps(job, city, serpapi_key)
            st.session_state.prospects = [r for r in raw if "website" not in r]

    if 'prospects' in st.session_state and st.session_state.prospects:
        for p in st.session_state.prospects:
            with st.expander(f"📍 {p.get('title', 'Inconnu')}"):
                c_act, c_res = st.columns([1, 2])
                pid = p.get('place_id', 'id')
                
                with c_act:
                    if st.button(f"✨ Générer Site", key=f"gen_{pid}"):
                        with st.spinner("Création..."):
                            code = generate_website_code(p.get('title'), job, city, p.get('address'), p.get('phone'))
                            st.session_state[f"html_{pid}"] = code
                    
                    if st.button(f"📧 Email", key=f"mail_{pid}"):
                        st.session_state[f"email_{pid}"] = generate_sales_email(p.get('title'))

                with c_res:
                    if f"html_{pid}" in st.session_state:
                        st.success("✅ Site généré !")
                        # NOUVELLE MÉTHODE DE TÉLÉCHARGEMENT
                        st.text("1. Cliquez sur le bouton copier en haut à droite du code.")
                        st.text("2. Collez dans un fichier 'site.html' sur votre PC.")
                        st.code(st.session_state[f"html_{pid}"], language="html")
                        
                        # Aperçu visuel en dessous
                        with st.expander("👁️ Voir l'aperçu visuel"):
                            st.components.v1.html(st.session_state[f"html_{pid}"], height=500, scrolling=True)

                    if f"email_{pid}" in st.session_state:
                        st.info("📧 Email de vente :")
                        st.code(st.session_state[f"email_{pid}"], language="markdown")

# --- ATELIER ---
with tab_editor:
    uploaded = st.file_uploader("📂 Charger un fichier HTML", type=['html'])
    if uploaded:
        html_content = uploaded.getvalue().decode("utf-8")
        st.components.v1.html(html_content, height=300, scrolling=True)
        
        instruction = st.text_area("Modifications demandées :")
        if st.button("🛠️ Appliquer"):
            with st.spinner("Travail en cours..."):
                new_html = modify_website_code(html_content, instruction)
                st.session_state['new_html'] = new_html
                st.rerun()
                
    if 'new_html' in st.session_state:
        st.divider()
        st.success("✅ Nouvelle version prête ! Copiez le code ci-dessous :")
        st.code(st.session_state['new_html'], language="html")
        st.components.v1.html(st.session_state['new_html'], height=500, scrolling=True)
