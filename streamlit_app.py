import streamlit as st
import openai
from serpapi import GoogleSearch
import resend

# --- CONFIGURATION ---
st.set_page_config(page_title="LocalHunter V4", page_icon="🏢", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #0f172a; color: white; border-radius: 8px; border: none; font-weight: bold; }
    div.stButton > button:hover { background-color: #334155; color: white; }
    .success-box { padding: 15px; background-color: #dcfce7; color: #166534; border-radius: 10px; margin-bottom: 10px; }
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
    except: return []

def generate_website_code(business_name, activity, city, address, phone):
    prompt = f"""
    Tu es un développeur Senior. Crée un site Web "Premium" (One-Page Scrolling) pour {business_name} ({activity}) à {city}.
    Infos: {address}, {phone}.
    
    Structure OBLIGATOIRE :
    1. Navbar Fixe. 2. Hero avec CTA. 3. Services (3 cartes). 4. Témoignages. 5. Contact + Map + Footer.
    
    Design : TailwindCSS. Couleurs : Slate-900 (fond), Amber-500 (boutons), White (texte).
    Règle : Code HTML complet UNIQUEMENT.
    """
    try:
        response = client.chat.completions.create(
            model="mistral-large-latest", messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except Exception as e: return f"<h1>Erreur IA: {e}</h1>"

def modify_website_code(current_html, instructions):
    prompt = f"""
    Tu es un expert en maintenance web. Voici un fichier HTML :
    
    {current_html[:15000]}... (code tronqué pour l'instruction)
    
    L'utilisateur veut cette modification précise : "{instructions}"
    
    Règles :
    1. Analyse le code et applique UNIQUEMENT la modification demandée.
    2. Ne casse pas le design TailwindCSS existant.
    3. Renvoie le code HTML COMPLET et corrigé.
    """
    try:
        # Note : On envoie le code entier si possible, attention à la limite de taille
        # Pour ce MVP on fait confiance à la fenêtre de contexte de Mistral
        full_prompt = f"Code HTML:\n{current_html}\n\nINSTRUCTION: {instructions}\n\nRenvoie le code HTML complet modifié :"
        
        response = client.chat.completions.create(
            model="mistral-large-latest", messages=[{"role": "user", "content": full_prompt}]
        )
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except Exception as e: return f"Erreur modification: {e}"

def generate_sales_email(business_name):
    prompt = f"Ecris un email court pour vendre ce site à {business_name}. Méthode AIDA. Ton bienveillant."
    try:
        response = client.chat.completions.create(
            model="mistral-large-latest", messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except: return "Erreur email"

# --- INTERFACE ---
st.title("🚀 LocalHunter - Suite Complète")

# On sépare les deux métiers : Chasseur vs Développeur
tab_hunter, tab_editor = st.tabs(["🔫 Mode Chasseur (Nouveaux)", "🔧 Atelier de Retouche (Clients)"])

# --- TAB 1 : CHASSEUR ---
with tab_hunter:
    col1, col2 = st.columns(2)
    with col1: job_input = st.text_input("Activité", "Coiffeur")
    with col2: city_input = st.text_input("Ville", "Bordeaux")

    if 'prospects' not in st.session_state: st.session_state.prospects = []

    if st.button("🔎 Lancer la recherche"):
        with st.status("Scan de la zone..."):
            raw = search_google_maps(job_input, city_input, serpapi_key)
            clean = []
            for res in raw:
                if "website" not in res:
                    clean.append({
                        "name": res.get("title", "Inconnu"),
                        "address": res.get("address", ""),
                        "phone": res.get("phone", ""),
                        "place_id": res.get("place_id", "id")
                    })
            st.session_state.prospects = clean
            st.success(f"{len(clean)} cibles identifiées.")

    if st.session_state.prospects:
        for p in st.session_state.prospects:
            with st.expander(f"📍 {p['name']}"):
                c1, c2 = st.columns([1, 1])
                pid = p['place_id']
                
                with c1:
                    if st.button(f"✨ Générer V1", key=f"gen_{pid}"):
                        with st.spinner("Construction..."):
                            html = generate_website_code(p['name'], job_input, city_input, p['address'], p['phone'])
                            st.session_state[f"html_{pid}"] = html
                with c2:
                    if st.button(f"📧 Email", key=f"mail_{pid}"):
                        st.session_state[f"email_{pid}"] = generate_sales_email(p['name'])

                if f"html_{pid}" in st.session_state:
                    st.download_button("💾 Télécharger HTML", st.session_state[f"html_{pid}"], file_name=f"{p['name']}.html")
                    st.components.v1.html(st.session_state[f"html_{pid}"], height=400, scrolling=True)
                
                if f"email_{pid}" in st.session_state:
                    st.info("Copiez l'email ci-dessous :")
                    st.code(st.session_state[f"email_{pid}"])

# --- TAB 2 : ATELIER DE RETOUCHE ---
with tab_editor:
    st.header("🔧 Modification de Site")
    st.markdown("Chargez un fichier HTML existant pour demander des modifications à l'IA.")
    
    uploaded_file = st.file_uploader("📂 Importer le fichier HTML du client", type=['html'])
    
    if uploaded_file is not None:
        # Lire le fichier
        string_data = uploaded_file.getvalue().decode("utf-8")
        st.success("Fichier chargé avec succès !")
        
        # Afficher l'aperçu actuel
        with st.expander("Voir le site actuel"):
            st.components.v1.html(string_data, height=400, scrolling=True)
            
        st.divider()
        
        # Zone de modification
        col_edit1, col_edit2 = st.columns([3, 1])
        with col_edit1:
            instruction = st.text_area("Quelles modifications voulez-vous ?", placeholder="Ex: Change le titre principal par 'Salon de Coiffure Bio'. Mets le fond en rose pâle.")
        with col_edit2:
            st.write("") # Spacer
            st.write("") 
            if st.button("🛠️ Lancer les retouches", type="primary"):
                if instruction:
                    with st.spinner("L'IA réécrit le code..."):
                        new_code = modify_website_code(string_data, instruction)
                        st.session_state['modified_html'] = new_code
                        st.success("Modifications terminées !")
                        st.rerun()

    # Résultat de la modification
    if 'modified_html' in st.session_state:
        st.divider()
        st.subheader("🎉 Nouvelle Version")
        
        dwn_col, view_col = st.columns([1, 3])
        with dwn_col:
            st.download_button(
                "💾 Télécharger V2", 
                st.session_state['modified_html'], 
                file_name="site_modifie.html",
                mime="text/html"
            )
        with view_col:
            st.components.v1.html(st.session_state['modified_html'], height=600, scrolling=True)
