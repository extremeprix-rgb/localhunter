import streamlit as st
import openai
from serpapi import GoogleSearch
import resend

# --- CONFIGURATION ---
st.set_page_config(page_title="LocalHunter V2", page_icon="🎯", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #2563eb; color: white; border-radius: 8px; font-weight: bold; border: none; }
    div.stButton > button:hover { background-color: #1d4ed8; color: white; }
    .email-box { background-color: #f1f5f9; padding: 20px; border-radius: 10px; border-left: 5px solid #2563eb; }
</style>
""", unsafe_allow_html=True)

# --- SECRETS ---
try:
    api_key = st.secrets.get("MISTRAL_KEY", st.secrets.get("OPENAI_KEY"))
    serpapi_key = st.secrets["SERPAPI_KEY"]
    resend.api_key = st.secrets["RESEND_KEY"]
    
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1"
    )
    api_ready = True
except Exception as e:
    st.error(f"⚠️ Erreur Config: {e}")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎯 LocalHunter")
    st.caption("V2.0 - Scraping + Site + Email")
    st.info("💡 **Workflow de Vente :**\n1. Scrape les prospects\n2. Génère le site\n3. Héberge le HTML (ex: Tiiny.host)\n4. Génère l'email de vente\n5. Envoie !")

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
    prompt = f"""
    Tu es un expert web. Crée le code HTML complet (une seule page) pour : {business_name} ({activity}) à {city}.
    Infos: {address}, {phone}.
    Design: TailwindCSS (CDN), moderne, épuré, professionnel.
    Contenu: Hero (accroche), Services (3 blocs), Contact (carte et infos).
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

def generate_sales_email(business_name, activity, city):
    prompt = f"""
    Rédige un email de prospection court et percutant pour "{business_name}" ({activity} à {city}).
    
    Ton rôle : Consultant Web local.
    Le but : Leur montrer que tu as DÉJÀ créé leur site web démo.
    
    Structure (Méthode AIDA) :
    1. Objet : Court et intriguant (ex: "J'ai créé le site de {business_name}...")
    2. Accroche : Compliment sur leur activité locale.
    3. Problème : "J'ai remarqué que vous n'aviez pas de site..."
    4. Solution : "J'ai pris l'initiative d'en créer un pour vous montrer le potentiel."
    5. Appel à l'action : "Cliquez ici pour le voir : [LIEN_DU_SITE]"
    
    Ton : Professionnel, bienveillant, pas "vendeur de tapis".
    """
    try:
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur génération email : {str(e)}"

# --- INTERFACE ---
st.title("🚀 Chasseur de Prospects & Vendeur")

col1, col2 = st.columns(2)
with col1: job_input = st.text_input("Activité", "Plombier")
with col2: city_input = st.text_input("Ville", "Nantes")

if 'prospects' not in st.session_state: st.session_state.prospects = []

if st.button("🔎 Lancer la recherche"):
    with st.status("Recherche en cours..."):
        raw_results = search_google_maps(job_input, city_input, serpapi_key)
        
        clean_prospects = []
        for res in raw_results:
            if "website" not in res:
                clean_prospects.append({
                    "name": res.get("title", "Nom inconnu"),
                    "address": res.get("address", "Adresse inconnue"),
                    "phone": res.get("phone", "Non renseigné"),
                    "place_id": res.get("place_id", "no_id")
                })
        
        st.session_state.prospects = clean_prospects
        st.write(f"✅ {len(clean_prospects)} prospects sans site trouvés.")

if st.session_state.prospects:
    st.divider()
    for p in st.session_state.prospects:
        with st.expander(f"📍 {p['name']}"):
            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.subheader("1. Le Site")
                if st.button(f"✨ Générer Site", key=f"site_{p['place_id']}"):
                    with st.spinner("Création du site..."):
                        html = generate_website_code(p['name'], job_input, city_input, p['address'], p['phone'])
                        st.session_state[f"html_{p['place_id']}"] = html # Sauvegarde en mémoire
            
            with c2:
                st.subheader("2. L'Email")
                if st.button(f"📝 Rédiger Email", key=f"mail_{p['place_id']}"):
                    with st.spinner("Rédaction de l'argumentaire..."):
                        email_txt = generate_sales_email(p['name'], job_input, city_input)
                        st.session_state[f"email_{p['place_id']}"] = email_txt

            # Affichage des résultats s'ils existent
            if f"html_{p['place_id']}" in st.session_state:
                st.markdown("---")
                st.download_button("📥 Télécharger le HTML (pour Tiiny.host)", 
                                 st.session_state[f"html_{p['place_id']}"], 
                                 file_name=f"{p['name']}.html")
                st.components.v1.html(st.session_state[f"html_{p['place_id']}"], height=400, scrolling=True)
            
            if f"email_{p['place_id']}" in st.session_state:
                st.markdown("---")
                st.markdown("**Copiez cet email :**")
                st.code(st.session_state[f"email_{p['place_id']}"], language="markdown")
                st.info("👉 N'oubliez pas de remplacer [LIEN_DU_SITE] par votre lien Tiiny.host avant d'envoyer !")
