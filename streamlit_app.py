import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time
import re
import base64
import hashlib

st.set_page_config(page_title="LocalHunter V13 (Deep Scan)", page_icon="🚀", layout="wide")

# CSS Interface Streamlit
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #0f172a; color: white; border-radius: 8px; font-weight: 600; padding: 0.5rem 1rem; }
    .stTextArea textarea { font-family: 'Courier New', monospace; font-size: 12px; }
    .badge-no-site { background-color: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .badge-weak-site { background-color: #ffedd5; color: #9a3412; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .badge-ok-site { background-color: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
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

# --- SEARCH ENGINE V2 (DEEP & SMART) ---

def analyze_website_quality(website_url):
    """Détermine si c'est un vrai site, pas de site, ou un site 'faible' (fb, pagesjaunes...)"""
    if not website_url:
        return "NONE" # Pas de site
    
    url = website_url.lower()
    weak_domains = ["facebook.com", "instagram.com", "linkedin.com", "pagesjaunes.fr", "business.site", "societe.com", "mappy.com"]
    
    for domain in weak_domains:
        if domain in url:
            return "WEAK" # Site faible (Opportunité !)
            
    return "OK" # Vrai site

def smart_search(job, city, api_key, max_pages):
    all_results = []
    seen = set()
    status_box = st.empty()
    
    # Paramètres optimisés pour le Deep Scan
    params = {
        "engine": "google_maps",
        "q": f"{job} {city}",
        "type": "search",
        "google_domain": "google.fr",
        "hl": "fr",
        "num": 20,
        "api_key": api_key
    }

    count_total = 0
    
    for page in range(max_pages):
        status_box.info(f"🛰️ Scan Page {page + 1}/{max_pages} en cours... ({count_total} trouvés)")
        
        params["start"] = page * 20
        
        try:
            search = GoogleSearch(params)
            data = search.get_dict()
            results = data.get("local_results", [])
            
            if not results:
                break
                
            for res in results:
                pid = res.get("place_id")
                if pid and pid not in seen:
                    # ANALYSE DU SITE ICI
                    website = res.get("website")
                    quality = analyze_website_quality(website)
                    
                    # On injecte l'analyse dans le résultat
                    res["site_quality"] = quality 
                    
                    all_results.append(res)
                    seen.add(pid)
                    count_total += 1
            
            time.sleep(1.5) # Pause pour éviter blocage
            
        except Exception as e:
            st.error(f"Erreur API Page {page+1}: {e}")
            break
            
    # TRI INTELLIGENT : NONE en premier, puis WEAK, puis OK
    priority_order = {"NONE": 0, "WEAK": 1, "OK": 2}
    all_results.sort(key=lambda x: priority_order[x["site_quality"]])
    
    status_box.success(f"✅ Scan terminé : {count_total} entreprises trouvées.")
    time.sleep(2)
    status_box.empty()
    return all_results

def generate_code(name, job, city, addr, tel):
    ts = int(time.time())
    
    # Prompt V12 (SEO & DESIGN) conservé
    prompt = f"""
    Agis comme un expert Web Designer & SEO. Crée un site One-Page HTML5 moderne (TailwindCSS) pour {name} ({job}) à {city}.
    Infos: Adresse: {addr}, Tel: {tel}.
    
    🎨 DESIGN & STYLE :
    - Utilise une police moderne (Google Fonts 'Inter' ou 'Poppins').
    - Palette de couleurs : Blanc, Gris ardoise (Slate-900), et une couleur d'accentuation forte (Blue-600 ou Indigo-600).
    - Utilise des ombres douces (shadow-xl), des coins arrondis (rounded-2xl) et des dégradés subtils.
    - Layout aéré, beaucoup d'espace blanc.

    🖼️ RÈGLE ABSOLUE IMAGES :
    - N'utilise JAMAIS 'background-image' en CSS. 
    - Utilise UNIQUEMENT des balises <img src="...">.
    - URLs obligatoires :
      1. Hero : src="https://loremflickr.com/1600/900/{job.replace(' ', ',')}?lock=1"
      2. About : src="https://loremflickr.com/800/800/{job.replace(' ', ',')}?lock=2"
      3. Service 1 : src="https://loremflickr.com/600/400/{job.replace(' ', ',')}?lock=3"
      4. Service 2 : src="https://loremflickr.com/600/400/{job.replace(' ', ',')}?lock=4"
      5. Service 3 : src="https://loremflickr.com/600/400/{job.replace(' ', ',')}?lock=5"

    📝 CONTENU SEO RICHE :
    1. Navbar Sticky + Logo + CTA.
    2. Hero Section : Titre H1, Sous-titre, CTA.
    3. Section Confiance (Stats).
    4. Section À Propos.
    5. Section Services (3 Cartes détaillées).
    6. Section Pourquoi Nous (Liste).
    7. Section FAQ (3 questions).
    8. Section Témoignages (2 avis).
    9. Footer complet.

    TECHNIQUE :
    - Formulaire : <form action="https://formsubmit.co/votre-email@gmail.com" method="POST" class="...">
    - Code HTML brut uniquement.
    """
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return clean_html_output(resp.choices[0].message.content)
    except: return "<!-- Erreur Gen -->"

def generate_email_prospection(name, site_status):
    context = "n'a pas de site internet" if site_status == "NONE" else "a un site peu optimisé (Facebook/PagesJaunes)"
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Rédige un Email de prospection à froid (Cold Emailing) méthode AIDA pour {name}. Contexte: Le prospect {context}. Propose une maquette gratuite moderne."}])
        return resp.choices[0].message.content
    except: return "Erreur Email"

# --- INTERFACE ---
st.title("LocalHunter V13 (Deep Scan & Filter Fix)")

tab1, tab2 = st.tabs(["🕵️ CHASSE", "🎨 ATELIER"])

with tab1:
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1: job = st.text_input("Activité", "Maçon")
    with c2: city = st.text_input("Ville", "Lyon")
    with c3: pages = st.number_input("Pages à scanner", 1, 10, 3) 
    with c4: 
        st.write("")
        st.write("")
        if st.button("LANCER SCAN", use_container_width=True):
            st.session_state.prospects = []
            results = smart_search(job, city, serpapi_key, pages)
            st.session_state.prospects = results

    if 'prospects' in st.session_state:
        results = st.session_state.prospects
        count_none = len([r for r in results if r["site_quality"] == "NONE"])
        count_weak = len([r for r in results if r["site_quality"] == "WEAK"])
        
        st.info(f"📊 Analyse : {len(results)} résultats affichés. {count_none} 🔴 Sans Site | {count_weak} 🟠 Site Faible (Facebook/PJ)")
            
        for p in results:
            # Code couleur visuel
            q = p["site_quality"]
            color_border = "border-left: 5px solid #ef4444;" if q == "NONE" else ("border-left: 5px solid #f97316;" if q == "WEAK" else "border-left: 5px solid #22c55e;")
            
            with st.container():
                # Card personnalisée en HTML/CSS dans Streamlit
                st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); {color_border}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h3 style="margin:0; font-size:1.1em; font-weight:bold;">{p.get('title')}</h3>
                            <p style="margin:0; color:#666; font-size:0.9em;">📍 {p.get('address')}</p>
                            <p style="margin:5px 0 0 0; font-size:0.85em;">
                                {f'<span class="badge-no-site">🔴 SANS SITE WEB</span>' if q == "NONE" else (f'<span class="badge-weak-site">🟠 SITE FAIBLE ({p.get("website")})</span>' if q == "WEAK" else f'<span class="badge-ok-site">🟢 SITE EXISTANT</span>')}
                            </p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Boutons d'action
                c_a, c_b = st.columns([1, 4])
                with c_a:
                    pid = p.get('place_id')
                    if st.button("⚡ Créer Site", key=f"gen_{pid}"):
                         with st.spinner("Génération..."):
                            code = generate_code(p.get('title'), job, city, p.get('address'), p.get('phone'))
                            st.session_state['final'] = code
                            st.success("Généré ! Voir Atelier.")
                with c_b:
                    if st.button("📧 Email", key=f"mail_{pid}"):
                        st.write(generate_email_prospection(p.get('title'), q))

with tab2:
    st.header("🔧 Atelier de Finition")
    
    if 'final' in st.session_state:
        st.download_button("💾 TÉLÉCHARGER LE SITE (index.html)", st.session_state['final'], "index.html", "text/html", use_container_width=True)
        st.divider()

    up_html = st.file_uploader("Charger un fichier HTML", type=['html'])
    
    if up_html:
        file_hash = hashlib.md5(up_html.getvalue()).hexdigest()
        if 'current_file_hash' not in st.session_state or st.session_state['current_file_hash'] != file_hash:
            st.session_state['final'] = up_html.getvalue().decode("utf-8")
            st.session_state['current_file_hash'] = file_hash

    if 'final' in st.session_state:
        current_html = st.session_state['final']
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("🖼️ Images")
            imgs = get_images_from_html(current_html)
            if imgs:
                opts = {i: f"Image #{i+1}" for i, _ in enumerate(imgs)}
                idx = st.selectbox("Choisir image", list(opts.keys()), format_func=lambda x: opts[x])
                
                # Preview
                try: 
                    if imgs[idx].startswith("http"): st.image(imgs[idx], width=150)
                except: pass

                u = st.file_uploader("Remplacer par", type=['jpg','png'])
                if u and st.button("Fusionner"):
                    b64 = image_to_base64(u)
                    if b64:
                        st.session_state['final'] = replace_specific_image(current_html, b64, idx)
                        st.rerun()
            else:
                st.warning("Pas d'images trouvées.")

        with c2:
            st.subheader("✍️ Texte & Email")
            if st.button("Configurer Email Client"):
                email = st.text_input("Email:")
                if email and "@" in email:
                    st.session_state['final'] = surgical_email_config(current_html, email)
                    st.success("OK")
            
            new_code = st.text_area("Éditer HTML", current_html, height=200)
            if st.button("Sauvegarder Texte"):
                st.session_state['final'] = new_code
                st.rerun()

        st.components.v1.html(st.session_state['final'], height=800, scrolling=True)
