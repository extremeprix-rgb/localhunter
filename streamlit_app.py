import streamlit as st
import openai
from serpapi import GoogleSearch
import resend

# --- CONFIGURATION ---
st.set_page_config(page_title="LocalHunter V1.1", page_icon="🎯", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #4F46E5; color: white; border-radius: 8px; border: none; font-weight: bold;}
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
    st.error("⚠️ PROBLÈME DE CLÉS : Vérifiez vos 'Secrets' dans Streamlit.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎯 LocalHunter V1.1")
    st.success("✅ Système connecté")
    st.info("💡 Astuce : Si vous avez peu de résultats, essayez une ville plus précise (ex: 'Paris 15', 'Lyon 2').")

# --- FONCTIONS AMÉLIORÉES ---
def search_google_maps(job, city, api_key):
    """Version améliorée avec pagination forcée"""
    try:
        params = {
            "engine": "google_maps",
            "q": f"{job} {city}",
            "type": "search",
            "google_domain": "google.fr",
            "hl": "fr",
            "num": 20, # Demande explicite de 20 résultats
            "api_key": api_key
        }
        search = GoogleSearch(params)
        results = search.get_dict().get("local_results", [])
        return results
    except Exception as e:
        st.error(f"Erreur SerpApi : {e}")
        return []

def generate_website_code(business_name, activity, city, address, phone):
    """Version plus rapide et robuste"""
    prompt = f"""
    Crée un code HTML complet (une seule page) pour un artisan : {business_name} ({activity}) à {city}.
    Infos: {address}, {phone}.
    Design: TailwindCSS (CDN).
    Structure: Header, Hero Section, Services, Contact.
    IMPORTANT: Donne UNIQUEMENT le code HTML, sans texte avant ni après.
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo", # Modèle rapide
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000 # Limite pour éviter le timeout
        )
        return response.choices[0].message.content.strip().replace("```html", "").replace("```", "")
    except Exception as e:
        return f"<h1>Erreur OpenAI</h1><p>{str(e)}</p><p>Vérifiez que vous avez des crédits sur votre compte OpenAI (Billing).</p>"

# --- INTERFACE ---
st.title("🚀 Chasseur de Prospects (Version Corrigée)")

col1, col2 = st.columns(2)
with col1: job_input = st.text_input("Activité", "Boulanger")
with col2: city_input = st.text_input("Ville", "Paris 11") # Plus précis = meilleurs résultats

if 'prospects' not in st.session_state: st.session_state.prospects = []

if st.button("🔎 Lancer le Scraping Profond"):
    with st.status("Analyse en cours...", expanded=True) as status:
        st.write("🌍 Interrogation de Google Maps (France)...")
        raw_results = search_google_maps(job_input, city_input, serpapi_key)
        
        st.write(f"📊 {len(raw_results)} résultats bruts récupérés.")
        
        clean_prospects = []
        for res in raw_results:
            # On garde ceux qui n'ont PAS de clé 'website'
            if "website" not in res:
                clean_prospects.append({
                    "name": res.get("title"),
                    "address": res.get("address"),
                    "phone": res.get("phone", "Non renseigné"),
                    "place_id": res.get("place_id")
                })
        
        st.session_state.prospects = clean_prospects
        
        if len(clean_prospects) > 0:
            status.update(label=f"Succès ! {len(clean_prospects)} prospects sans site web trouvés.", state="complete", expanded=False)
        else:
            status.update(label="Aucun prospect sans site trouvé. Essayez une autre ville.", state="error")

if st.session_state.prospects:
    st.divider()
    for p in st.session_state.prospects:
        with st.expander(f"📍 {p['name']} ({p['address']})"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"📞 **{p['phone']}**")
            with c2:
                if st.button(f"✨ Générer Site", key=p['place_id']):
                    with st.spinner("L'IA travaille... (Attendez 10-15s)"):
                        html = generate_website_code(p['name'], job_input, city_input, p['address'], p['phone'])
                        if "Erreur" in html:
                            st.error(html) # Affiche l'erreur technique si il y en a une
                        else:
                            st.components.v1.html(html, height=500, scrolling=True)
                            st.download_button("Télécharger HTML", html, file_name=f"{p['name']}.html")
