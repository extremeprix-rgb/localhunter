import streamlit as st
import openai
from serpapi import GoogleSearch
import time
import re
import base64
import hashlib
import urllib.parse
import zipfile
import io
from PIL import Image

st.set_page_config(page_title="LocalHunter V40 (SMS Persuasif)", page_icon="🎯", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #0f172a; color: white; border-radius: 8px; font-weight: 600; }
    .badge-none { background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #ef4444; }
    .badge-weak { background-color: #ffedd5; color: #9a3412; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #f97316; }
    .badge-ok { background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
    .step-box { background-color: #f0fdf4; border: 1px solid #16a34a; padding: 20px; border-radius: 10px; margin: 15px 0; }
    .btn-link { 
        display: inline-block; 
        background-color: #16a34a; 
        color: white !important; 
        padding: 8px 16px; 
        border-radius: 6px; 
        text-decoration: none; 
        font-weight: bold; 
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Secrets Management
try:
    api_key = st.secrets.get("MISTRAL_KEY", st.secrets.get("OPENAI_KEY"))
    serpapi_key = st.secrets.get("SERPAPI_KEY") 
    client = openai.OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
except:
    st.error("⚠️ ERREUR CONFIGURATION : Les clés API ne sont pas détectées.")
    st.stop()

if not serpapi_key:
    st.error("⚠️ ERREUR CRITIQUE : La clé SERPAPI_KEY est manquante.")
    st.stop()

# --- INITIALISATION STATE ---
if 'prospects' not in st.session_state:
    st.session_state.prospects = []
if 'final' not in st.session_state:
    st.session_state.final = ""
if 'current_prospect' not in st.session_state:
    st.session_state.current_prospect = None # Pour stocker le prospect en cours de travail

# --- FONCTIONS TECHNIQUES ---

def clean_html_output(raw_text):
    text = raw_text.replace("```html", "").replace("```", "").strip()
    if "<!DOCTYPE html>" not in text[:50].upper():
        text = "<!DOCTYPE html>\n" + text
    if "charset=" not in text.lower():
        text = text.replace("<head>", '<head>\n<meta charset="UTF-8">', 1)
    start = text.find("<!DOCTYPE html>")
    end = text.find("</html>")
    if start != -1 and end != -1: return text[start : end + 7]
    return text

def create_zip_archive(html_content):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        info = zipfile.ZipInfo("index.html")
        info.date_time = time.localtime(time.time())[:6]
        info.compress_type = zipfile.ZIP_DEFLATED
        zip_file.writestr(info, html_content.encode('utf-8'))
    return zip_buffer.getvalue()

def image_to_base64(uploaded_file):
    if uploaded_file is None: return None
    try:
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P"): image = image.convert("RGB")
        image.thumbnail((1000, 1000))
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=75)
        b64_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{b64_str}"
    except: return None

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

# --- MOTEUR DE SCAN ---

def check_site_quality(url):
    if not url: return "NONE"
    u = url.lower()
    weak_list = ["facebook", "instagram", "linkedin", "pagesjaunes", "societe.com", "mappy", "business.site"]
    if any(weak in u for weak in weak_list): return "WEAK"
    return "OK"

def smart_search(job, city, api_key, max_pages):
    all_results = []
    seen_ids = set()
    status_container = st.empty()
    gps_context = None 
    
    # Stratégie de requêtes multiples pour maximiser les résultats
    queries = [f"{job} {city}", f"Entreprise {job} {city}", f"Artisan {job} {city}"]
    current_query_idx = 0

    for page in range(max_pages):
        start_index = page * 20
        status_container.info(f"⏳ Scan Page {page + 1}/{max_pages} (Requête: {queries[current_query_idx]})...")
        
        params = {
            "engine": "google_maps",
            "q": queries[current_query_idx],
            "type": "search",
            "google_domain": "google.fr",
            "hl": "fr",
            "num": 20,
            "api_key": api_key
        }

        if start_index > 0:
            if gps_context:
                params["start"] = start_index
                params["ll"] = gps_context
            else:
                # Si pas de GPS, on change de requête pour "reset" la pagination sur une autre recherche
                if current_query_idx < len(queries) - 1:
                    current_query_idx += 1
                    # On recommence une pagination à 0 pour la nouvelle requête
                    params["q"] = queries[current_query_idx]
                    params["start"] = 0 
        
        try:
            client_search = GoogleSearch(params)
            data = client_search.get_dict()
            
            if "error" in data:
                st.warning(f"Note API : {data['error']}")
                break
            
            # GPS Lock
            if not gps_context and "local_results" in data and data["local_results"]:
                first = data["local_results"][0]
                lat = first.get("gps_coordinates", {}).get("latitude")
                lng = first.get("gps_coordinates", {}).get("longitude")
                if lat and lng:
                    gps_context = f"@{lat},{lng},14z"

            local_results = data.get("local_results", [])
            
            if not local_results:
                # Si plus de résultat sur cette requête, on tente la suivante
                if current_query_idx < len(queries) - 1:
                    current_query_idx += 1
                    continue
                else:
                    break 
            
            for res in local_results:
                pid = res.get("place_id", str(hash(res.get("title"))))
                if pid not in seen_ids:
                    res["site_quality"] = check_site_quality(res.get("website"))
                    all_results.append(res)
                    seen_ids.add(pid)
            
            time.sleep(1.0)
            
        except Exception as e:
            st.error(f"Erreur technique : {e}")
            break
            
    status_container.success(f"✅ Terminé : {len(all_results)} résultats.")
    time.sleep(2)
    status_container.empty()
    
    order = {"NONE": 0, "WEAK": 1, "OK": 2}
    all_results.sort(key=lambda x: order[x["site_quality"]])
    return all_results

# --- GENERATION ---
def generate_code(name, job, city, addr, tel):
    prompt = f"""
    Agis comme un expert Web Designer. Crée un site One-Page HTML5 (TailwindCSS) pour {name} ({job}) à {city}.
    Infos: {addr}, {tel}.
    
    IMAGES (Strictement <img src="...">) :
    1. Hero: "https://loremflickr.com/1600/900/{job.replace(' ', ',')}?lock=1"
    2. About: "https://loremflickr.com/800/800/{job.replace(' ', ',')}?lock=2"
    3. Services: 3 images random lock=3,4,5.
    
    STRUCTURE :
    - Navbar, Hero (H1+CTA), Confiance (Stats), About, Services (3 cartes), FAQ, Footer.
    - Formulaire fonctionnel: <form action="https://formsubmit.co/votre-email@gmail.com" method="POST">
    - Design : Moderne, épuré, ombres douces (shadow-lg), rounded-xl.
    """
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return clean_html_output(resp.choices[0].message.content)
    except: return "<!-- Erreur Gen -->"

def generate_prospection_content(name, type_content, link_url):
    
    # Prompt optimisé pour la conversion
    if type_content == "EMAIL":
        if link_url:
            prompt = f"""
            Rédige un Email de prospection AIDA ultra-convaincant pour l'entreprise "{name}".
            
            STRUCTURE :
            1. Accroche : "J'ai remarqué que vous n'aviez pas de site web..."
            2. Intérêt : "Aujourd'hui, 80% des clients cherchent sur Google avant d'appeler."
            3. Désir : "J'ai pris l'initiative de créer une maquette complète pour vous, gratuitement."
            4. Action : "Cliquez ici pour voir votre site : {link_url}"
            5. Conclusion : "Je peux le mettre en ligne cette semaine. On s'appelle ?"
            
            Règle : Ton professionnel, empathique, direct. Pas de blabla marketing lourd.
            """
        else:
            prompt = f"""
            Rédige un Email de prospection AIDA pour "{name}" (Artisan/PME).
            Objet : Votre visibilité sur Google
            Corps : 
            - Bonjour, je suis développeur web local.
            - J'ai vu que vous n'aviez pas de site. C'est dommage pour votre référencement.
            - J'ai déjà préparé une maquette démo spécialement pour vous.
            - Est-ce que je peux vous envoyer le lien par SMS ou Email ?
            - Cordialement.
            """
            
    elif type_content == "SMS":
        if link_url:
            prompt = f"""
            Rédige un SMS de prospection ultra-persuasif pour l'artisan "{name}". (Max 250 caractères).
            
            Structure :
            1. Approche directe : "Bonjour, j'ai vu que vous n'aviez pas de site."
            2. La solution (Gratuite) : "J'ai pris la liberté de vous en créer un pour vous montrer le potentiel."
            3. Le lien : "{link_url}"
            4. Appel à l'action : "On peut en discuter 5min ?"
            
            Ton : Professionnel, serviable, pas de spam.
            """
        else:
            prompt = f"""
            Rédige un SMS de prospection intriguant pour "{name}" (Max 160 caractères).
            Message : "Bonjour, je suis développeur dans le coin. J'ai créé une maquette de site web complète pour votre entreprise (gratuitement). Sur quel numéro puis-je vous envoyer le lien pour que vous jetiez un œil ?"
            """
            
    elif type_content == "SCRIPT":
        prompt = f"""
        Rédige un script de prospection téléphonique (Cold Call) pour appeler {name}.
        
        Phase 1 : Introduction (10s)
        "Bonjour, c'est [Nom], je suis voisin à [Ville]. Je ne vous vends rien, j'ai juste une surprise pour vous."
        
        Phase 2 : Le Pitch (20s)
        "J'ai vu que vous n'aviez pas de site web. J'en ai créé un hier soir pour vous montrer ce que ça donnerait. C'est bluffant."
        
        Phase 3 : Closing
        "Je vous envoie le lien par SMS maintenant ? Vous me dites ce que vous en pensez ?"
        
        Phase 4 : Traitement objection "Pas intéressé"
        "C'est gratuit de regarder. Ça ne vous engage à rien."
        """
    
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return resp.choices[0].message.content 
    except: return "Erreur de génération IA."

# --- UI ---
st.title("LocalHunter V40 (SMS Persuasif)")

tab1, tab2 = st.tabs(["🕵️ CHASSE", "🎨 ATELIER (Edit & Send)"])

with tab1:
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1: job = st.text_input("Activité", "Maçon")
    with c2: city = st.text_input("Ville", "Lyon")
    with c3: pages = st.number_input("Pages (20 res/page)", 1, 10, 3)
    with c4: 
        st.write("")
        st.write("")
        if st.button("LANCER LE SCAN", use_container_width=True):
            results = smart_search(job, city, serpapi_key, pages)
            if results:
                st.session_state.prospects = results

    if st.session_state.prospects:
        results = st.session_state.prospects
        none_cnt = len([x for x in results if x['site_quality'] == "NONE"])
        
        st.info(f"🎯 CIBLES EN MÉMOIRE : {none_cnt} Sans Site | {len(results)} Total")
        
        for p in results:
            q = p["site_quality"]
            badge = '<span class="badge-none">🔴 PAS DE SITE</span>' if q == "NONE" else ('<span class="badge-weak">🟠 SITE FAIBLE</span>' if q == "WEAK" else '<span class="badge-ok">🟢 OK</span>')
            
            with st.expander(f"{'🔴' if q=='NONE' else ('🟠' if q=='WEAK' else '🟢')} {p.get('title')} - {p.get('address')}"):
                st.markdown(f"**Statut Web :** {badge} <br> **Tel:** {p.get('phone')}", unsafe_allow_html=True)
                
                # Bouton unique pour envoyer vers l'Atelier
                if st.button(f"🛠️ TRAVAILLER SUR CE PROSPECT", key=f"work_{p.get('place_id')}", use_container_width=True):
                    # Génération automatique du site si pas déjà fait
                    with st.spinner("Création du site en cours..."):
                        code = generate_code(p.get('title'), job, city, p.get('address'), p.get('phone'))
                        st.session_state.final = code 
                        # On stocke les infos du prospect actuel pour l'atelier
                        st.session_state.current_prospect = p
                        st.success("Site créé ! Allez dans l'onglet ATELIER pour le finir et l'envoyer.")

with tab2:
    st.header("🔧 Atelier & Démarchage")
    
    # Vérification qu'un site est chargé
    if not st.session_state.final:
        st.info("👈 Commencez par sélectionner un prospect dans l'onglet CHASSE.")
        
        # Option de secours : Upload manuel
        up_html = st.file_uploader("Ou chargez un fichier HTML existant", type=['html'])
        if up_html:
            st.session_state.final = up_html.getvalue().decode("utf-8")
            st.rerun()
    
    else:
        # Affiche le nom du prospect si dispo
        if st.session_state.current_prospect:
            p_curr = st.session_state.current_prospect
            st.success(f"Dossier en cours : **{p_curr.get('title')}** ({p_curr.get('phone')})")
        
        # --- SECTION 1 : CUSTOMISATION ---
        with st.expander("1️⃣ CUSTOMISATION DU SITE (Images & Textes)", expanded=True):
            html = st.session_state.final
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("🖼️ Images")
                imgs = get_images_from_html(html)
                if imgs:
                    idx = st.selectbox("Choisir image", range(len(imgs)), format_func=lambda x: f"Image #{x+1}")
                    up_img = st.file_uploader("Nouvelle image", type=['jpg','png'], key="u_img")
                    if up_img and st.button("Remplacer"):
                        b64 = image_to_base64(up_img)
                        if b64:
                            new_html = replace_specific_image(html, b64, idx)
                            st.session_state.final = new_html 
                            st.rerun()
            
            with c2:
                st.subheader("✍️ Config")
                em = st.text_input("Email Client (Formulaire)")
                if st.button("Valider Email"):
                    if "@" in em:
                        new_html = surgical_email_config(html, em)
                        st.session_state.final = new_html
                        st.success("OK")
                        st.rerun()
                
                if st.button("Sauvegarder les modifs manuelles"):
                    # Logique pour un text area si besoin, ici simplifié
                    pass

        # --- SECTION 2 : PUBLICATION ---
        with st.expander("2️⃣ PUBLICATION & LIEN", expanded=True):
            st.markdown("""
            <div class="step-box">
                <b>MÉTHODE :</b>
                1. Copiez le code HTML ci-dessous.
                2. Allez sur <a href="https://gist.github.com" target="_blank" class="btn-link">GIST ↗</a>, collez, créez le Gist.
                3. Prenez l'URL "Raw" et transformez-la sur <a href="https://raw.githack.com" target="_blank" class="btn-link">GITHACK ↗</a>.
                4. Collez le lien final ci-dessous pour générer votre message.
            </div>
            """, unsafe_allow_html=True)
            
            st.text_area("Code HTML à copier :", st.session_state.final, height=150)
            
            # Input Lien Unique
            hosted_link = st.text_input("🔗 COLLEZ LE LIEN FINAL ICI (ex: raw.githack.com/...)", key="final_link")

        # --- SECTION 3 : DÉMARCHAGE ---
        if st.session_state.current_prospect:
            p_name = st.session_state.current_prospect.get('title')
            p_email = st.session_state.current_prospect.get('email', '')
        else:
            p_name = "Le Client"
            p_email = ""

        st.markdown("### 📢 3. ENVOYER AU CLIENT")
        
        t_email, t_sms, t_script = st.tabs(["📧 EMAIL", "📱 SMS", "📞 TÉLÉPHONE"])
        
        with t_email:
            if st.button("Générer l'Email"):
                body = generate_prospection_content(p_name, "EMAIL", hosted_link)
                st.text_area("Sujet : Votre site web est prêt", body, height=250)
                
                subject = urllib.parse.quote(f"Site web pour {p_name}")
                body_enc = urllib.parse.quote(body)
                st.markdown(f'<a href="mailto:{p_email}?subject={subject}&body={body_enc}" target="_blank" style="background-color:#ea580c;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:bold;display:block;text-align:center;">🚀 ENVOYER MAINTENANT</a>', unsafe_allow_html=True)

        with t_sms:
            if st.button("Générer le SMS"):
                sms_txt = generate_prospection_content(p_name, "SMS", hosted_link)
                st.code(sms_txt, language="text")
                st.info("💡 Copiez ce texte et envoyez-le depuis votre téléphone.")
        
        with t_script:
            if st.button("Générer le Script"):
                script_txt = generate_prospection_content(p_name, "SCRIPT", hosted_link)
                st.text_area("Script d'appel", script_txt, height=300)

        # Preview Final
        st.markdown("---")
        st.subheader("Aperçu du site actuel")
        st.components.v1.html(st.session_state.final, height=600, scrolling=True)
