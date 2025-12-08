import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time
import re

st.set_page_config(page_title="LocalHunter V9 (Formulaires)", page_icon="🏢", layout="wide")

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

# --- FONCTION NETTOYAGE ---
def clean_html_output(raw_text):
    text = raw_text.replace("```html", "").replace("```", "").strip()
    start_marker = "<!DOCTYPE html>"
    end_marker = "</html>"
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)
    if start_idx != -1 and end_idx != -1:
        return text[start_idx : end_idx + len(end_marker)]
    return text

# --- MOTEUR DE RECHERCHE (V7) ---
def smart_search(job, city, api_key, max_pages):
    all_results = []
    seen = set()
    status_box = st.empty()
    status_box.info(f"📍 Scan de {city}...")
    
    try:
        params = {"engine": "google_maps", "q": f"{job} {city}", "type": "search", "google_domain": "google.fr", "hl": "fr", "num": 20, "api_key": api_key}
        search = GoogleSearch(params)
        data = search.get_dict()
        results = data.get("local_results", [])
        for res in results:
            pid = res.get("place_id")
            if pid and pid not in seen:
                all_results.append(res)
                seen.add(pid)

        # Pagination simple
        ll_token = None
        try:
            url = data.get("search_metadata", {}).get("google_maps_url", "")
            match = re.search(r'@([-0-9.]+),([-0-9.]+),([0-9.]+)z', url)
            if match: ll_token = f"@{match.group(1)},{match.group(2)},{match.group(3)}z"
        except: pass

        if ll_token and max_pages > 1:
            for page in range(1, max_pages):
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
    except Exception as e: st.error(f"Erreur: {e}")

    status_box.success(f"✅ {len(all_results)} résultats.")
    time.sleep(2)
    status_box.empty()
    return all_results

# --- GENERATEURS ---
def generate_code(name, job, city, addr, tel):
    # On force l'IA à mettre un formulaire générique au début
    prompt = f"""
    Crée un site One-Page HTML (TailwindCSS) pour {name} ({job}) à {city}. Adresse: {addr}, Tel: {tel}.
    
    IMPORTANT POUR LE FORMULAIRE DE CONTACT :
    Utilise EXACTEMENT cette balise pour le formulaire :
    <form action="https://formsubmit.co/votre-email@gmail.com" method="POST" class="space-y-4">
    
    Structure: Navbar, Hero, Services, Contact. Commence par <!DOCTYPE html>.
    """
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return clean_html_output(resp.choices[0].message.content)
    except: return "<!-- Erreur Gen -->"

def modify_code(html, ins):
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Modifie ce HTML: {ins}. Renvoie tout le code HTML complet."}])
        return clean_html_output(resp.choices[0].message.content)
    except: return html

def configure_form(html_content, client_email):
    """Fonction Python (pas IA) pour changer l'email du formulaire à coup sûr"""
    # Regex pour trouver l'action du formulaire et la remplacer
    pattern = r'action="https://formsubmit.co/[^"]*"'
    replacement = f'action="https://formsubmit.co/{client_email}"'
    
    # On ajoute aussi un champ caché pour désactiver le captcha si besoin
    hidden_field = '<input type="hidden" name="_captcha" value="false">'
    
    new_html = re.sub(pattern, replacement, html_content)
    
    # Petite astuce : on s'assure que le formulaire est en POST
    new_html = new_html.replace('method="get"', 'method="POST"').replace('method="GET"', 'method="POST"')
    
    return new_html

def generate_email_prospection(name):
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Email prospection court AIDA pour {name}."}])
        return resp.choices[0].message.content
    except: return "Erreur Email"

# --- INTERFACE ---
st.title("LocalHunter V9 (Formulaires)")

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
                        st.session_state[f"e_{pid}"] = generate_email_prospection(p.get('title'))
                
                with c_b:
                    if f"h_{pid}" in st.session_state:
                        st.text("Code prêt (Email formulaire par défaut: votre-email@gmail.com)")
                        st.code(st.session_state[f"h_{pid}"], language="html")
                    if f"e_{pid}" in st.session_state:
                        st.text_area("Mail", st.session_state[f"e_{pid}"])

with tab2:
    st.header("🔧 Configuration Finale (Avant livraison)")
    up = st.file_uploader("1. Charger le fichier HTML du site vendu", type=['html'])
    
    if up:
        html = up.getvalue().decode("utf-8")
        st.success("Fichier chargé.")
        
        c_edit1, c_edit2 = st.columns(2)
        
        with c_edit1:
            st.subheader("A. Retouche Design (IA)")
            ins = st.text_input("Ex: Change le fond en bleu nuit")
            if st.button("Appliquer Design"):
                with st.spinner("Retouche..."):
                    st.session_state['new'] = modify_code(html, ins)
                    st.rerun()

        with c_edit2:
            st.subheader("B. Activer Formulaire (Python)")
            client_email = st.text_input("Email du client (pour recevoir les messages)", placeholder="boulangerie@orange.fr")
            if st.button("Configurer Email"):
                if client_email and "@" in client_email:
                    st.session_state['new'] = configure_form(html, client_email)
                    st.success(f"✅ Formulaire configuré vers {client_email} !")
                    st.rerun()
                else:
                    st.error("Email invalide")

    if 'new' in st.session_state:
        st.divider()
        st.success("🎉 VERSION FINALE PRÊTE À UPLOADER SUR O2SWITCH")
        st.code(st.session_state['new'], language="html")
        with st.expander("Voir résultat"):
            st.components.v1.html(st.session_state['new'], height=400, scrolling=True)
