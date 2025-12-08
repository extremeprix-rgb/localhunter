import streamlit as st
import openai
from serpapi import GoogleSearch
import resend

# --- CONFIGURATION ---
st.set_page_config(page_title="LocalHunter Ultimate", page_icon="💎", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #0f172a; color: white; border-radius: 8px; border: none; font-weight: bold; }
    div.stButton > button:hover { background-color: #334155; color: white; }
    .stTextArea textarea { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# --- SECRETS ---
try:
    api_key = st.secrets.get("MISTRAL_KEY", st.secrets.get("OPENAI_KEY"))
    serpapi_key = st.secrets["SERPAPI_KEY"]
    resend.api_key = st.secrets["RESEND_KEY"]
    
    client = openai.OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
    api_ready = True
except Exception as e:
    st.error(f"⚠️ Erreur Config: {e}")
    st.stop()

# --- FONCTIONS ---
def search_google_maps(job, city, api_key):
    try:
        params = {
            "engine": "google_maps", "q": f"{job} {city}", "type": "search",
            "google_domain": "google.fr", "hl": "fr", "num": 20, "api_key": api_key
        }
        search = GoogleSearch(params)
        return search.get_dict().get("local_results", [])
    except Exception as e:
        return []

def generate_website_code(business_name, activity, city, address, phone):
    prompt = f"""
    Tu es un développeur Senior. Crée un site Web "Premium" (One-Page Scrolling) pour {business_name} ({activity}) à {city}.
    
    Structure OBLIGATOIRE :
    1. Navbar Fixe (Sticky) : Accueil, À Propos, Services, Contact.
    2. Hero Section : Grande image de fond, Titre accrocheur, bouton "Prendre RDV".
    3. Section "À Propos" : Texte rassurant sur l'artisanat local.
    4. Section "Nos Services" : 3 cartes (Cards) détaillées avec icônes.
    5. Section "Témoignages" : 2 faux avis clients positifs.
    6. Footer : Mentions légales, adresse ({address}), tel ({phone}).
    
    Design : Utilise TailwindCSS. Couleurs professionnelles (Bleu nuit, Doré, Blanc).
    Règle : Code HTML complet, prêt à l'emploi. Pas de markdown.
    """
    try:
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except Exception as e:
        return f"<h1>Erreur IA</h1><p>{str(e)}</p>"

def modify_website_code(current_html, instructions):
    prompt = f"""
    Voici un code HTML existant :
    {current_html}
    
    L'utilisateur veut cette modification : "{instructions}"
    
    Tâche : Réécris le code HTML en appliquant la modification. Garde le reste intact.
    Règle : Renvoie UNIQUEMENT le code HTML complet.
    """
    try:
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except Exception as e:
        return current_html # On renvoie l'ancien si erreur

def generate_sales_email(business_name, activity):
    prompt = f"Rédige un email de prospection B2B court pour {business_name} ({activity}). Ton : Expert Web. Objectif : Montrer le site démo créé."
    try:
        response = client.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except:
        return "Erreur email"

# --- INTERFACE ---
st.title("💎 Usine à Sites Web (Premium Edition)")
st.caption("Scraping • Génération Premium • Retouches • Emailing")

col1, col2 = st.columns(2)
with col1: job_input = st.text_input("Activité", "Rénovation")
with col2: city_input = st.text_input("Ville", "Lyon")

if 'prospects' not in st.session_state: st.session_state.prospects = []

if st.button("🔎 Trouver des clients"):
    with st.status("Chasse en cours..."):
        raw = search_google_maps(job_input, city_input, serpapi_key)
        clean = []
        for res in raw:
            if "website" not in res:
                clean.append({
                    "name": res.get("title", "Inconnu"),
                    "address": res.get("address", "Inconnue"),
                    "phone": res.get("phone", "Non renseigné"),
                    "place_id": res.get("place_id", "id")
                })
        st.session_state.prospects = clean
        st.write(f"✅ {len(clean)} prospects qualifiés.")

if st.session_state.prospects:
    st.divider()
    for p in st.session_state.prospects:
        with st.expander(f"🏢 {p['name']} ({p['address']})"):
            
            # Gestion des IDs uniques pour le State
            pid = p['place_id']
            html_key = f"html_{pid}"
            email_key = f"email_{pid}"

            # Zone 1 : Génération
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button(f"✨ Créer Site Premium", key=f"btn_gen_{pid}"):
                    with st.spinner("Architecture du site en cours..."):
                        html = generate_website_code(p['name'], job_input, city_input, p['address'], p['phone'])
                        st.session_state[html_key] = html
            
            with c2:
                if st.button(f"📧 Préparer Email", key=f"btn_mail_{pid}"):
                    mail = generate_sales_email(p['name'], job_input)
                    st.session_state[email_key] = mail

            # Zone 2 : Modification & Affichage
            if html_key in st.session_state:
                st.markdown("---")
                st.subheader("🎨 Studio de Retouche")
                
                # Input de modification
                modif_txt = st.text_input("Demander une retouche à l'IA", placeholder="Ex: Change le bleu en vert, Ajoute une section Tarifs...", key=f"input_{pid}")
                
                if st.button("🛠️ Appliquer la modification", key=f"btn_modif_{pid}"):
                    if modif_txt:
                        with st.spinner("L'IA applique vos corrections..."):
                            new_html = modify_website_code(st.session_state[html_key], modif_txt)
                            st.session_state[html_key] = new_html
                            st.success("Modifications appliquées !")
                            st.rerun()

                # Visualisation
                tab1, tab2 = st.tabs(["👁️ Aperçu du Site", "💾 Télécharger"])
                with tab1:
                    st.components.v1.html(st.session_state[html_key], height=600, scrolling=True)
                with tab2:
                    st.download_button("Télécharger HTML", st.session_state[html_key], file_name=f"{p['name']}_v3.html")

            if email_key in st.session_state:
                st.info("📧 Email généré (à copier)")
                st.code(st.session_state[email_key])
