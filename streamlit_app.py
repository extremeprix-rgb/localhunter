import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time
import re
import base64

st.set_page_config(page_title="LocalHunter V11 (Base64)", page_icon="🏆", layout="wide")

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

# --- FONCTIONS TECHNIQUES ---

def clean_html_output(raw_text):
    text = raw_text.replace("```html", "").replace("```", "").strip()
    start = text.find("<!DOCTYPE html>")
    end = text.find("</html>")
    if start != -1 and end != -1: return text[start : end + 7]
    return text

def image_to_base64(uploaded_file):
    """Transforme une image en chaîne de caractères pour l'incruster dans le HTML"""
    bytes_data = uploaded_file.getvalue()
    b64_str = base64.b64encode(bytes_data).decode()
    # On devine le mime type (jpg/png)
    mime = "image/png" if uploaded_file.name.endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{b64_str}"

def get_images_from_html(html_content):
    """Trouve toutes les URLs d'images dans le code pour créer le menu déroulant"""
    # Cherche src="..." ou src='...'
    pattern = r'<img[^>]+src=["\']([^"\']*)["\']'
    return [m.group(1) for m in re.finditer(pattern, html_content)]

def replace_specific_image(html_content, image_data, index):
    """Remplace une image spécifique (par son index) par la version Base64"""
    # Capture: (début tag + src=") (contenu url) (fin quote + fin tag)
    # flag re.S (dotall) n'est pas nécessaire ici car img est souvent sur 1 ligne, mais attention si multiline
    pattern = r'(<img[^>]+src=["\'])([^"\']*)(["\'][^>]*>)'
    matches = list(re.finditer(pattern, html_content))
    
    if 0 <= index < len(matches):
        m = matches[index]
        # Reconstruction chirurgicale
        # On remplace UNIQUEMENT cette occurrence dans le texte
        # Astuce : on split le texte en 3 parties : avant, match, après
        start = m.start()
        end = m.end()
        
        new_tag = f"{m.group(1)}{image_data}{m.group(3)}"
        return html_content[:start] + new_tag + html_content[end:]
    return html_content

def surgical_email_config(html_content, email):
    pattern = r'action="https://formsubmit.co/[^"]*"'
    replacement = f'action="https://formsubmit.co/{email}"'
    new_html = re.sub(pattern, replacement, html_content)
    return new_html

# --- SEARCH & GEN ---
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
        try:
            url = data.get("search_metadata", {}).get("google_maps_url", "")
            match = re.search(r'@([-0-9.]+),([-0-9.]+),([0-9.]+)z', url)
            if match and max_pages > 1:
                ll_token = f"@{match.group(1)},{match.group(2)},{match.group(3)}z"
                for page in range(1, max_pages):
                    try:
                        params["start"] = page * 20
                        params["ll"] = ll_token
                        sub = GoogleSearch(params).get_dict().get("local_results", [])
                        if not sub: break
                        for r in sub:
                            if r.get("place_id") not in seen:
                                all_results.append(r)
                                seen.add(r.get("place_id"))
                        time.sleep(1)
                    except: break
        except: pass
    except Exception as e: st.error(str(e))
    status_box.success(f"✅ {len(all_results)} résultats.")
    time.sleep(1)
    status_box.empty()
    return all_results

def generate_code(name, job, city, addr, tel):
    # Prompt amélioré pour un site plus complet
    prompt = f"""
    Crée un site One-Page HTML (TailwindCSS) COMPLET pour {name} ({job}) à {city}.
    Infos: Adresse: {addr}, Tel: {tel}.
    
    IMAGES OBLIGATOIRES (Utilise ces URLs placeholders):
    1. Hero: "https://loremflickr.com/1200/800/{job.replace(' ', ',')}?random=1"
    2. Section Histoire: "https://loremflickr.com/800/600/{job.replace(' ', ',')}?random=2"
    3. Section Services (3 images icones): Pas besoin d'images lourdes, utilise des emojis.
    
    STRUCTURE REQUISE :
    1. Navbar (Logo + Tel)
    2. Hero Section (Grand titre, appel à l'action, image de fond)
    3. Section "Notre Histoire" : Texte de présentation + Photo à droite. Raconte que l'entreprise est experte depuis 10 ans.
    4. Section Services (3 cartes)
    5. Section Témoignages (2 avis clients fictifs)
    6. Contact : Formulaire <form action="https://formsubmit.co/votre-email@gmail.com" method="POST">
    
    TECHNIQUE :
    - Commence par <!DOCTYPE html>
    - Ajoute onerror="this.src='https://placehold.co/600x400'" sur TOUTES les balises <img>.
    """
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return clean_html_output(resp.choices[0].message.content)
    except: return "<!-- Erreur Gen -->"

def generate_email_prospection(name):
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Email AIDA pour {name}."}])
        return resp.choices[0].message.content
    except: return "Erreur Email"

# --- INTERFACE ---
st.title("LocalHunter V11 (Images Incassables Multiples)")

tab1, tab2 = st.tabs(["CHASSE", "ATELIER (Customisation)"])

with tab1:
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1: job = st.text_input("Activité", "Maçon")
    with c2: city = st.text_input("Ville", "Bordeaux")
    with c3: pages = st.number_input("Pages", 1, 5, 2)
    with c4: 
        st.write("")
        st.write("")
        if st.button("SCAN", use_container_width=True):
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
                        # On envoie direct en session finale pour l'atelier
                        st.session_state['final'] = st.session_state[f"h_{pid}"]
                        st.success("Site généré ! Allez dans l'onglet Atelier.")
                    if st.button("📧 Email", key=f"m_{pid}"):
                        st.session_state[f"e_{pid}"] = generate_email_prospection(p.get('title'))
                with c_b:
                    if f"h_{pid}" in st.session_state:
                        st.text_area("Code", st.session_state[f"h_{pid}"], height=100)
                    if f"e_{pid}" in st.session_state:
                        st.text_area("Mail", st.session_state[f"e_{pid}"])

with tab2:
    st.header("🔧 Customisation Pro")
    
    # Zone de chargement
    up_html = st.file_uploader("1. Charger le fichier HTML", type=['html'])
    
    # Logique pour récupérer le HTML (soit upload, soit généré)
    current_html = ""
    if up_html:
        current_html = up_html.getvalue().decode("utf-8")
        # Si on upload un nouveau, on écrase la session
        if 'final' not in st.session_state or st.session_state['final'] != current_html:
             st.session_state['final'] = current_html
    elif 'final' in st.session_state:
        current_html = st.session_state['final']

    if current_html:
        st.success("Fichier HTML actif.")
        
        col_img, col_mail = st.columns(2)
        
        with col_img:
            st.subheader("🖼️ Gestion des Images")
            
            # Analyse des images
            images_found = get_images_from_html(current_html)
            
            if not images_found:
                st.warning("Aucune balise <img> trouvée.")
            else:
                # Création du menu déroulant
                # On crée une liste de tuples (index, description)
                options = list(range(len(images_found)))
                
                def format_func(i):
                    url = images_found[i]
                    name = "Hero/Header" if i == 0 else f"Image #{i+1}"
                    return f"{name} ({url[:30]}...)"
                
                selected_index = st.selectbox(
                    "Quelle image remplacer ?", 
                    options=options,
                    format_func=format_func
                )
                
                up_img = st.file_uploader("Nouvelle photo (JPG/PNG)", type=['jpg', 'jpeg', 'png'], key="img_uploader")
                
                if up_img and st.button("Fusionner l'image sélectionnée"):
                    b64_img = image_to_base64(up_img)
                    # Mise à jour
                    new_html = replace_specific_image(current_html, b64_img, selected_index)
                    st.session_state['final'] = new_html
                    st.success(f"Image #{selected_index+1} remplacée !")
                    st.rerun()

        with col_mail:
            st.subheader("📧 Email Formulaire")
            client_email = st.text_input("Email du client :")
            if st.button("Configurer Email"):
                if "@" in client_email:
                    new_html = surgical_email_config(current_html, client_email)
                    st.session_state['final'] = new_html
                    st.success("Email configuré !")
                    st.rerun()

    # Preview & Download
    if 'final' in st.session_state:
        st.divider()
        st.markdown("### ⬇️ Téléchargement")
        
        st.download_button(
            "💾 Télécharger index.html", 
            st.session_state['final'],
            file_name="index.html",
            mime="text/html",
            use_container_width=True
        )
        
        st.markdown("### 👁️ Aperçu")
        st.components.v1.html(st.session_state['final'], height=600, scrolling=True)
