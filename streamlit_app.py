import streamlit as st
import openai
from serpapi import GoogleSearch
import resend

# --- CONFIGURATION ---
st.set_page_config(page_title="LocalHunter (Mistral Edition)", page_icon="🇫🇷", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #f59e0b; color: white; border-radius: 8px; border: none; font-weight: bold;}
    div.stButton > button:hover { background-color: #d97706; color: white; }
</style>
""", unsafe_allow_html=True)

# --- SECRETS ---
try:
    # On cherche la clé MISTRAL ou OPENAI
    api_key = st.secrets.get("MISTRAL_KEY", st.secrets.get("OPENAI_KEY"))
    serpapi_key = st.secrets["SERPAPI_KEY"]
    resend.api_key = st.secrets["RESEND_KEY"]
    
    # Client Mistral
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1"
    )
    api_ready = True
except Exception as e:
    st.error(f"⚠️ Erreur de configuration : {e}")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🇫🇷 LocalHunter")
    st.caption("Propulsé par Mistral AI")
    if api_ready:
        st.success("✅ Système connecté")

# --- FONCTIONS ---
def search_google_maps(job, city, api_key):
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
        results = search.get_dict().get("local_results", [])
        return results
    except Exception as e:
        st.error(f"Erreur SerpApi : {e}")
        return []

def generate_website_code(business_name, activity, city, address, phone):
    """Génération via Mistral"""
    prompt = f"""
    Tu es un expert web. Crée le code HTML complet (une seule page) pour : {business_name} ({activity}) à {city}.
    Infos: {address}, {phone}.
    Design: Utilise TailwindCSS (CDN) pour un look très moderne.
    Contenu: Hero section, Services, Contact.
    Règle: Donne UNIQUEMENT le code HTML brut.
    """
    
    try:
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except Exception as e:
        return f"<h1>Erreur IA</h1><p>{str(e)}</p>"

# --- INTERFACE ---
st.title("🇫🇷 Chasseur de Prospects (Mistral Edition)")

col1, col2 = st.columns(2)
with col1: job_input = st.text_input("Activité", "Plombier")
with col2: city_input = st.text_input("Ville", "Nantes")

if 'prospects' not in st.session_state: st.session_state.prospects = []

if st.button("🔎 Lancer la recherche"):
    with st.status("Recherche en cours..."):
        raw_results = search_google_maps(job_input, city_input, serpapi_key)
        
        # --- CORRECTIF DU BUG ---
        # On transforme les données brutes en format propre pour éviter l'erreur de clé
        clean_prospects = []
        for res in raw_results:
            if "website" not in res:
                clean_prospects.append({
                    "name": res.get("title", "Nom inconnu"), # On sécurise avec .get()
                    "address": res.get("address", "Adresse inconnue"),
                    "phone": res.get("phone", "Non renseigné"),
                    "place_id": res.get("place_id", "no_id")
                })
        
        st.session_state.prospects = clean_prospects
        st.write(f"✅ {len(clean_prospects)} prospects sans site trouvés.")

if st.session_state.prospects:
    st.divider()
    for p in st.session_state.prospects:
        # Maintenant p['name'] existe forcément
        with st.expander(f"📍 {p['name']}"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"📞 {p['phone']}")
                st.write(f"🏠 {p['address']}")
            with c2:
                if st.button(f"✨ Générer Site", key=p['place_id']):
                    with st.spinner("Mistral rédige le code..."):
                        html = generate_website_code(p['name'], job_input, city_input, p['address'], p['phone'])
                        st.components.v1.html(html, height=500, scrolling=True)
                        st.download_button("Télécharger HTML", html, file_name=f"{p['name']}.html")
