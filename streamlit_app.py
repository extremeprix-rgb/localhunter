import streamlit as st
import openai
from serpapi import GoogleSearch
import time
import re
import base64
import hashlib
import urllib.parse

st.set_page_config(page_title="LocalHunter V23 (Free Hosting)", page_icon="⚡", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #0f172a; color: white; border-radius: 8px; font-weight: 600; }
    .badge-none { background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #ef4444; }
    .badge-weak { background-color: #ffedd5; color: #9a3412; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #f97316; }
    .badge-ok { background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
    .step-box { background-color: #f8fafc; border: 1px dashed #94a3b8; padding: 15px; border-radius: 8px; margin: 10px 0; }
    a.host-btn { display: inline-block; background-color: #10b981; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 10px; margin-right: 10px;}
    a.host-btn:hover { background-color: #059669; }
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

    for page in range(max_pages):
        start_index = page * 20
        status_container.info(f"⏳ Scan Page {page + 1}/{max_pages}...")
        
        params = {
            "engine": "google_maps",
            "q": f"{job} {city}",
            "type": "search",
            "google_domain": "google.fr",
            "hl": "fr",
            "num": 20,
            "api_key": api_key
        }

        if start_index > 0:
            if not gps_context:
                status_container.warning("⚠️ Arrêt pagination : Google demande une localisation GPS précise non trouvée en page 1.")
                break
            params["start"] = start_index
            params["ll"] = gps_context
        
        try:
            client_search = GoogleSearch(params)
            data = client_search.get_dict()
            
            if "error" in data:
                st.warning(f"Note API : {data['error']}")
                break
            
            if page == 0:
                try:
                    meta_url = data.get("search_metadata", {}).get("google_maps_url", "")
                    match = re.search(r'@([-0-9.]+),([-0-9.]+),([0-9.]+)z', meta_url)
                    if match:
                        gps_context = f"@{match.group(1)},{match.group(2)},{match.group(3)}z"
                except: pass
                
                if not gps_context and "local_results" in data and data["local_results"]:
                    first = data["local_results"][0]
                    lat = first.get("gps_coordinates", {}).get("latitude")
                    lng = first.get("gps_coordinates", {}).get("longitude")
                    if lat and lng:
                        gps_context = f"@{lat},{lng},14z"

            local_results = data.get("local_results", [])
            
            if not local_results:
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
    
    if type_content == "EMAIL":
        if link_url:
            prompt = f"Rédige un Email AIDA très court pour {name}. J'ai créé une maquette de leur site, voici le lien : {link_url}. Donne juste le corps du mail, pas de politesses inutiles."
        else:
            prompt = f"Rédige un Email AIDA très court pour {name} pour proposer une maquette de site web. Donne juste le corps du mail."
            
    elif type_content == "SMS":
        if link_url:
            prompt = f"Rédige un SMS pour {name} (max 160 caractères). 'Bonjour, j'ai fait une maquette de votre site : {link_url}. Qu'en pensez-vous ?'."
        else:
            prompt = f"Rédige un SMS pour {name} (max 160 caractères) pour proposer une démo de site web."
            
    elif type_content == "SCRIPT":
        prompt = f"Script appel téléphonique direct pour {name}. But: avoir le 06 pour envoyer le lien par SMS. Pas de blabla."
    
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return resp.choices[0].message.content.replace('"', '') # Clean quotes
    except: return "Erreur Gen"

# --- UI ---
st.title("LocalHunter V23 (Free Hosting)")

tab1, tab2 = st.tabs(["🕵️ CHASSE", "🎨 ATELIER"])

with tab1:
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1: job = st.text_input("Activité", "Maçon")
    with c2: city = st.text_input("Ville", "Lyon")
    with c3: pages = st.number_input("Pages (20 res/page)", 1, 10, 3)
    with c4: 
        st.write("")
        st.write("")
        if st.button("LANCER LE SCAN", use_container_width=True):
            st.session_state.prospects = []
            st.session_state.prospects = smart_search(job, city, serpapi_key, pages)

    if 'prospects' in st.session_state and st.session_state.prospects:
        results = st.session_state.prospects
        none_cnt = len([x for x in results if x['site_quality'] == "NONE"])
        
        st.info(f"🎯 CIBLES : {none_cnt} Sans Site | {len(results)} Total")
        
        for p in results:
            q = p["site_quality"]
            badge = '<span class="badge-none">🔴 PAS DE SITE</span>' if q == "NONE" else ('<span class="badge-weak">🟠 SITE FAIBLE</span>' if q == "WEAK" else '<span class="badge-ok">🟢 OK</span>')
            
            with st.expander(f"{'🔴' if q=='NONE' else ('🟠' if q=='WEAK' else '🟢')} {p.get('title')} - {p.get('address')}"):
                st.markdown(f"**Statut Web :** {badge} <br> **Tel:** {p.get('phone')}", unsafe_allow_html=True)
                
                c_a, c_b = st.columns(2)
                with c_a:
                    if st.button("⚡ Générer Site", key=f"g_{p.get('place_id')}"):
                        with st.spinner("Création..."):
                            code = generate_code(p.get('title'), job, city, p.get('address'), p.get('phone'))
                            st.session_state['final'] = code
                            st.success("Fait ! Voir Atelier.")

                st.markdown("---")
                
                # Input Lien Unique
                hosted_link = st.text_input("🔗 Lien Hébergé (Static.app)", key=f"lnk_{p.get('place_id')}")

                t_email, t_sms, t_script = st.tabs(["📧 Email", "📱 SMS", "📞 Téléphone"])
                
                with t_email:
                    if st.button("📝 Rédiger Email", key=f"gen_e_{p.get('place_id')}"):
                        body = generate_prospection_content(p.get('title'), "EMAIL", hosted_link)
                        st.code(body, language="text")
                        
                        detected_email = p.get('email', "")
                        subject = urllib.parse.quote(f"Site web pour {p.get('title')}")
                        body_enc = urllib.parse.quote(body)
                        st.markdown(f'<a href="mailto:{detected_email}?subject={subject}&body={body_enc}" target="_blank" style="background-color:#ea580c;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;">🚀 Ouvrir Boite Mail</a>', unsafe_allow_html=True)

                with t_sms:
                    if st.button("📱 Rédiger SMS", key=f"gen_s_{p.get('place_id')}"):
                        sms_txt = generate_prospection_content(p.get('title'), "SMS", hosted_link)
                        st.code(sms_txt, language="text")
                
                with t_script:
                    if st.button("🗣️ Rédiger Script", key=f"gen_c_{p.get('place_id')}"):
                        script_txt = generate_prospection_content(p.get('title'), "SCRIPT", hosted_link)
                        st.text_area("Script", script_txt, height=200)

with tab2:
    st.header("🔧 Atelier & Publication")
    
    if 'final' in st.session_state:
        st.markdown("""
        <div class="step-box">
            <b>🚀 ÉTAPE 1 : HÉBERGEMENT GRATUIT (Alternative Tiiny)</b><br>
            1. Téléchargez le fichier HTML.<br>
            2. Ouvrez <a href="https://static.app" target="_blank" class="host-btn">STATIC.APP ↗</a> (Meilleure alternative gratuite).<br>
            3. Si ça bloque, essayez <a href="https://surge.sh" target="_blank" class="host-btn">Surge.sh ↗</a> (Ligne de commande).<br>
            4. Copiez le lien, revenez dans CHASSE et collez-le pour générer le SMS.
        </div>
        """, unsafe_allow_html=True)
        
        st.download_button("💾 TÉLÉCHARGER LE SITE (index.html)", st.session_state['final'], "index.html", "text/html", use_container_width=True)
        st.divider()

    up_html = st.file_uploader("Charger HTML", type=['html'])
    if up_html:
        h = hashlib.md5(up_html.getvalue()).hexdigest()
        if st.session_state.get('chash') != h:
            st.session_state['final'] = up_html.getvalue().decode("utf-8")
            st.session_state['chash'] = h

    if 'final' in st.session_state:
        html = st.session_state['final']
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
                        st.session_state['final'] = replace_specific_image(html, b64, idx)
                        st.rerun()
        
        with c2:
            st.subheader("✍️ Texte & Email")
            em = st.text_input("Email Client")
            if st.button("Configurer Email"):
                if "@" in em:
                    st.session_state['final'] = surgical_email_config(html, em)
                    st.success("OK")
            
            new_txt = st.text_area("Editer HTML", html, height=200)
            if st.button("Sauvegarder"):
                st.session_state['final'] = new_txt
                st.rerun()

        st.components.v1.html(st.session_state['final'], height=800, scrolling=True)
