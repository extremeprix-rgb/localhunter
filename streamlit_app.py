import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time
import re
import base64
import hashlib

st.set_page_config(page_title="LocalHunter V12 (SEO & Design)", page_icon="💎", layout="wide")

# CSS Interface Streamlit
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #0f172a; color: white; border-radius: 8px; font-weight: 600; padding: 0.5rem 1rem; }
    .stTextArea textarea { font-family: 'Courier New', monospace; font-size: 12px; }
    h1 { color: #0f172a; }
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
    if uploaded_file is None: return None
    try:
        bytes_data = uploaded_file.getvalue()
        b64_str = base64.b64encode(bytes_data).decode()
        mime = "image/png" if uploaded_file.name.lower().endswith(".png") else "image/jpeg"
        return f"data:{mime};base64,{b64_str}"
    except Exception as e:
        st.error(f"Erreur conversion image: {e}")
        return None

def get_images_from_html(html_content):
    pattern = r'<img\s+[^>]*?src=["\']([^"\']*?)["\']'
    return [m.group(1) for m in re.finditer(pattern, html_content, re.IGNORECASE | re.DOTALL)]

def replace_specific_image(html_content, image_data, index):
    pattern = r'(<img\s+[^>]*?src=["\'])([^"\']*?)(["\'][^>]*?>)'
    matches = list(re.finditer(pattern, html_content, re.IGNORECASE | re.DOTALL))
    if 0 <= index < len(matches):
        m = matches[index]
        start = m.start()
        end = m.end()
        new_tag = f"{m.group(1)}{image_data}{m.group(3)}"
        return html_content[:start] + new_tag + html_content[end:]
    return html_content

def surgical_email_config(html_content, email):
    pattern = r'action=["\']https://formsubmit\.co/[^"\']*["\']'
    replacement = f'action="https://formsubmit.co/{email}"'
    if re.search(pattern, html_content):
        return re.sub(pattern, replacement, html_content)
    else:
        return html_content.replace('<form', f'<form action="https://formsubmit.co/{email}"')

# --- SEARCH & GEN ---

def smart_search(job, city, api_key, max_pages):
    all_results = []
    seen = set()
    status_box = st.empty()
    
    # Configuration de base
    params = {
        "engine": "google_maps",
        "q": f"{job} {city}",
        "type": "search",
        "google_domain": "google.fr",
        "hl": "fr",
        "num": 20, # Maximum autorisé par SerpApi par appel
        "api_key": api_key
    }

    # Boucle sur le nombre de pages demandées
    for page in range(max_pages):
        status_box.info(f"📍 Scan de {city} en cours... (Page {page + 1}/{max_pages})")
        
        # On décale le début des résultats (0, 20, 40, 60, 80)
        params["start"] = page * 20
        
        try:
            search = GoogleSearch(params)
            data = search.get_dict()
            results = data.get("local_results", [])
            
            # Si pas de résultats sur cette page, on arrête
            if not results:
                break
                
            for res in results:
                pid = res.get("place_id")
                # On ajoute si on ne l'a pas déjà vu
                if pid and pid not in seen:
                    all_results.append(res)
                    seen.add(pid)
            
            # Petite pause pour éviter de brusquer l'API
            time.sleep(1)
            
        except Exception as e:
            st.error(f"Erreur sur la page {page+1}: {str(e)}")
            break
            
    status_box.success(f"✅ Scan terminé : {len(all_results)} entreprises analysées au total.")
    time.sleep(2)
    status_box.empty()
    return all_results

def generate_code(name, job, city, addr, tel):
    ts = int(time.time())
    
    prompt = f"""
    Agis comme un expert Web Designer & SEO. Crée un site One-Page HTML5 moderne (TailwindCSS) pour {name} ({job}) à {city}.
    Infos: Adresse: {addr}, Tel: {tel}.
    
    🎨 DESIGN & STYLE :
    - Utilise une police moderne (Google Fonts 'Inter' ou 'Poppins').
    - Palette de couleurs : Blanc, Gris ardoise (Slate-900), et une couleur d'accentuation forte (Blue-600 ou Indigo-600).
    - Utilise des ombres douces (shadow-xl), des coins arrondis (rounded-2xl) et des dégradés subtils.
    - Layout aéré, beaucoup d'espace blanc (padding generoux).

    🖼️ RÈGLE ABSOLUE IMAGES (Pour compatibilité outil de remplacement) :
    - N'utilise JAMAIS 'background-image' en CSS. 
    - Utilise UNIQUEMENT des balises <img src="..." class="object-cover ...">.
    - URLs obligatoires (LoremFlickr avec locks différents pour varier) :
      1. Hero (Pleine largeur absolute) : src="https://loremflickr.com/1600/900/{job.replace(' ', ',')}?lock=1"
      2. About (Carrée) : src="https://loremflickr.com/800/800/{job.replace(' ', ',')}?lock=2"
      3. Service 1 : src="https://loremflickr.com/600/400/{job.replace(' ', ',')}?lock=3"
      4. Service 2 : src="https://loremflickr.com/600/400/{job.replace(' ', ',')}?lock=4"
      5. Service 3 : src="https://loremflickr.com/600/400/{job.replace(' ', ',')}?lock=5"

    📝 STRUCTURE SEO & CONTENU RICHE :
    1. <head> : Ajoute meta description optimisée SEO locale ("Meilleur {job} à {city}..."), Title pertinent.
    2. Navbar Sticky : Logo (Texte gras), Liens (Accueil, Services, FAQ, Contact), Bouton CTA "Devis Gratuit".
    3. Hero Section : Titre H1 accrocheur ("L'expert {job} de référence à {city}"), Sous-titre persuasif, CTA, Image de fond sombre avec overlay.
    4. Section "Confiance" (Barre de stats) : "10+ Années d'expérience", "500+ Chantiers", "100% Satisfait".
    5. Section "À Propos" : Titre H2. Texte de 150 mots sur l'expertise, le sérieux, l'ancrage local à {city}. Image à droite.
    6. Section "Nos Services" : 3 Cartes modernes (Ombre au survol). Titre H3 + Description détaillée de 3 lignes par service.
    7. Section "Pourquoi Nous ?" : Liste à puces avec icones (FontAwesome ou SVG inline) : Devis rapide, Garantie décennale (si applicable), Prix transparents.
    8. Section FAQ (Accordéon ou Grille) : 3 questions fréquentes pour ce métier avec réponses rassurantes.
    9. Section Témoignages : 2 avis clients fictifs avec étoiles ⭐⭐⭐⭐⭐.
    10. Footer : Mentions légales, Copyright, Adresse complète, Liens SEO.

    TECHNIQUE :
    - Formulaire : <form action="https://formsubmit.co/votre-email@gmail.com" method="POST" class="bg-white p-8 rounded-2xl shadow-lg">
    - Pas de Markdown, donne uniquement le code HTML brut.
    """
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return clean_html_output(resp.choices[0].message.content)
    except: return "<!-- Erreur Gen -->"

def generate_email_prospection(name):
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Rédige un Email de prospection à froid (Cold Emailing) méthode AIDA pour {name}. Ton court, professionnel, qui propose de voir la maquette du site gratuitement."}])
        return resp.choices[0].message.content
    except: return "Erreur Email"

# --- INTERFACE ---
st.title("LocalHunter V12 (SEO & Design Pro)")

tab1, tab2 = st.tabs(["🕵️ CHASSE (Scan & Gen)", "🎨 ATELIER (Custom & Images)"])

with tab1:
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1: job = st.text_input("Activité", "Maçon")
    with c2: city = st.text_input("Ville", "Lyon")
    with c3: pages = st.number_input("Pages Google (20 résultats/page)", 1, 5, 3) # J'ai augmenté à 5 pages max
    with c4: 
        st.write("")
        st.write("")
        if st.button("LANCER SCAN", use_container_width=True):
            st.session_state.prospects = []
            raw = smart_search(job, city, serpapi_key, pages)
            clean = [r for r in raw if "website" not in r] # Filtre ceux qui n'ont pas de site
            st.session_state.prospects = clean
            st.session_state.stats = (len(raw), len(clean))

    if 'prospects' in st.session_state:
        if 'stats' in st.session_state:
            tot, kep = st.session_state.stats
            st.info(f"📊 Résultat du scan : {tot} fiches trouvées, dont {kep} SANS site web (Vos cibles !).")
            
        for p in st.session_state.prospects:
            with st.expander(f"📍 {p.get('title')} ({p.get('address')})"):
                c_a, c_b = st.columns([1, 2])
                pid = p.get('place_id')
                with c_a:
                    if st.button("⚡ Générer Site Pro", key=f"g_{pid}"):
                        with st.spinner("Rédaction du contenu SEO et Design en cours..."):
                            code = generate_code(p.get('title'), job, city, p.get('address'), p.get('phone'))
                            st.session_state[f"h_{pid}"] = code
                            st.session_state['final'] = code # Envoi auto vers Atelier
                            st.success("Site créé ! Allez dans l'Atelier.")
                    if st.button("📧 Email d'approche", key=f"m_{pid}"):
                        st.session_state[f"e_{pid}"] = generate_email_prospection(p.get('title'))
                with c_b:
                    if f"h_{pid}" in st.session_state:
                        st.text_area("Code HTML", st.session_state[f"h_{pid}"], height=100)
                    if f"e_{pid}" in st.session_state:
                        st.text_area("Brouillon Email", st.session_state[f"e_{pid}"])

with tab2:
    st.header("🔧 Atelier de Finition")
    
    # Bouton de téléchargement GLOBAL (Toujours visible si un site existe)
    if 'final' in st.session_state:
        st.download_button(
            label="💾 TÉLÉCHARGER LE SITE COMPLET (index.html)", 
            data=st.session_state['final'],
            file_name="index.html",
            mime="text/html",
            use_container_width=True
        )
        st.divider()

    # Upload HTML
    up_html = st.file_uploader("Charger un fichier HTML (si pas généré à l'instant)", type=['html'])
    
    if up_html:
        file_hash = hashlib.md5(up_html.getvalue()).hexdigest()
        if 'current_file_hash' not in st.session_state or st.session_state['current_file_hash'] != file_hash:
            st.session_state['final'] = up_html.getvalue().decode("utf-8")
            st.session_state['current_file_hash'] = file_hash
            st.success("Fichier chargé.")

    if 'final' in st.session_state:
        current_html = st.session_state['final']
        
        col_img, col_text = st.columns([1, 1])
        
        # --- IMAGES ---
        with col_img:
            st.subheader("🖼️ Remplacement Images")
            st.caption("Changez les images génériques par les photos du client (Camion, Équipe...).")
            
            images_found = get_images_from_html(current_html)
            
            if not images_found:
                st.warning("Aucune image modifiable trouvée.")
            else:
                img_options = {i: f"Image #{i+1} : {url[-20:]}..." for i, url in enumerate(images_found)}
                selected_index = st.selectbox(
                    "Choisir l'emplacement :", 
                    options=list(img_options.keys()),
                    format_func=lambda x: img_options[x]
                )
                
                # Preview Miniature
                try:
                    url_preview = images_found[selected_index]
                    if url_preview.startswith("http"):
                        st.image(url_preview, caption="Actuelle", width=200)
                except: pass
                
                up_img = st.file_uploader("Votre photo (JPG/PNG)", type=['jpg', 'png', 'jpeg'], key=f"u_{selected_index}")
                
                if up_img and st.button("Fusionner l'image", use_container_width=True):
                    b64_img = image_to_base64(up_img)
                    if b64_img:
                        new_html = replace_specific_image(current_html, b64_img, selected_index)
                        st.session_state['final'] = new_html
                        st.success("✅ Remplacée ! (Regardez l'aperçu en bas)")
                        st.rerun()

        # --- TEXTE & EMAIL ---
        with col_text:
            st.subheader("✍️ Contenu & Contact")
            
            with st.expander("Configuration Email (Formulaire)"):
                client_email = st.text_input("Email du client (pour recevoir les devis) :")
                if st.button("Valider Email"):
                    if "@" in client_email:
                        new_html = surgical_email_config(current_html, client_email)
                        st.session_state['final'] = new_html
                        st.success("Formulaire connecté !")
                        st.rerun()
            
            with st.expander("Éditeur Rapide (Code HTML)"):
                edited_html = st.text_area("Code", value=current_html, height=200)
                if st.button("Sauvegarder les textes"):
                    st.session_state['final'] = edited_html
                    st.success("Mis à jour !")
                    st.rerun()

        st.markdown("---")
        st.subheader("👁️ Aperçu en direct")
        st.components.v1.html(st.session_state['final'], height=800, scrolling=True)
    
    else:
        st.info("👈 Commencez par l'onglet CHASSE pour trouver un client et créer son site.")
