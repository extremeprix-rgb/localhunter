import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time
import re
import base64
import hashlib

st.set_page_config(page_title="LocalHunter V17 (Final)", page_icon="🎯", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #0f172a; color: white; border-radius: 8px; font-weight: 600; }
    .badge-none { background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #ef4444; }
    .badge-weak { background-color: #ffedd5; color: #9a3412; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #f97316; }
    .badge-ok { background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
</style>
""", unsafe_allow_html=True)

# Secrets
try:
    api_key = st.secrets.get("MISTRAL_KEY", st.secrets.get("OPENAI_KEY"))
    serpapi_key = st.secrets.get("SERPAPI_KEY") 
    client = openai.OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
except:
    st.error("⚠️ Clés API manquantes (.streamlit/secrets.toml).")
    st.stop()

if not serpapi_key:
    st.error("⚠️ Clé SERPAPI_KEY manquante.")
    st.stop()

# --- HELPER FUNCTIONS ---

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

# --- SCAN LOGIC (V15 GPS FIX) ---

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
            "start": start_index,
            "num": 20,
            "api_key": api_key
        }
        
        if gps_context and page > 0:
            params["ll"] = gps_context
        
        try:
            client_search = GoogleSearch(params)
            data = client_search.get_dict()
            
            if "error" in data:
                st.warning(f"Note SerpApi (Page {page+1}) : {data['error']}")
                if "Missing location" in data['error']:
                    st.error("⚠️ Erreur GPS. Précisez la ville (ex: 'Lyon France').")
                break
            
            if page == 0:
                try:
                    meta_url = data.get("search_metadata", {}).get("google_maps_url", "")
                    match = re.search(r'@([-0-9.]+),([-0-9.]+),([0-9.]+)z', meta_url)
                    if match:
                        gps_context = f"@{match.group(1)},{match.group(2)},{match.group(3)}z"
                except: pass

            local_results = data.get("local_results", [])
            
            if not local_results:
                break 
            
            for res in local_results:
                pid = res.get("place_id", str(hash(res.get("title"))))
                if pid not in seen_ids:
                    res["site_quality"] = check_site_quality(res.get("website"))
                    all_results.append(res)
                    seen_ids.add(pid)
            
            time.sleep(1.5)
            
        except Exception as e:
            st.error(f"Erreur technique : {e}")
            break
            
    status_container.success(f"✅ Terminé : {len(all_results)} résultats.")
    time.sleep(2)
    status_container.empty()
    
    order = {"NONE": 0, "WEAK": 1, "OK": 2}
    all_results.sort(key=lambda x: order[x["site_quality"]])
    return all_results

# --- GENERATION AI ---

def generate_code(name, job, city, addr, tel):
    prompt = f"""
    Agis comme un expert Web Designer. Crée un site One-Page HTML5 (TailwindCSS) pour {name} ({job}) à {city}.
    Infos: {addr}, {tel}.
    
    IMAGES OBLIGATOIRES (Strictement <img src="...">) :
    1. Hero: "https://loremflickr.com/1600/900/{job.replace(' ', ',')}?lock=1"
    2. About: "https://loremflickr.com/800/800/{job.replace(' ', ',')}?lock=2"
    3. Services: 3 images random lock=3,4,5.
    
    STRUCTURE :
    - Navbar, Hero (H1+CTA), Confiance (Stats), About, Services (3 cartes), FAQ, Footer.
    - Formulaire: <form action="https://formsubmit.co/votre-email@gmail.com" method="POST">
    - Design : Moderne, épuré, ombres douces (shadow-lg), rounded-xl.
    """
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return clean_html_output(resp.choices[0].message.content)
    except: return "<!-- Erreur Gen -->"

def generate_email_prospection(name, status):
    context = "n'a pas de site web" if status == "NONE" else "a une visibilité limitée"
    try:
        resp = client.chat.completions.create(model="mistral-large-latest", messages=[{"role": "user", "content": f"Email court AIDA pour {name} ({context}). Propose maquette gratuite."}])
        return resp.choices[0].message.content
    except: return "Erreur Email"

# --- MAIN UI ---

st.title("LocalHunter V17 (Final)")
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
        weak_cnt = len([x for x in results if x['site_quality'] == "WEAK"])
        
        st.info(f"🎯 CIBLES : {none_cnt} Sans Site | {weak_cnt} Site Faible | {len(results)} Total")
        
        for p in results:
            q = p["site_quality"]
            badge = '<span class="badge-none">🔴 PAS DE SITE</span>' if q == "NONE" else ('<span class="badge-weak">🟠 SITE FAIBLE</span>' if q == "WEAK" else '<span class="badge-ok">🟢 OK</span>')
            
            with st.expander(f"{'🔴' if q=='NONE' else ('🟠' if q=='WEAK' else '🟢')} {p.get('title')} - {p.get('address')}"):
                st.markdown(f"**Statut Web :** {badge} <br> **Tel:** {p.get('phone')}", unsafe_allow_html=True)
                
                colA, colB = st.columns(2)
                with colA:
                    if st.button("⚡ Générer Site", key=f"g_{p.get('place_id')}"):
                        with st.spinner("Création..."):
                            code = generate_code(p.get('title'), job, city, p.get('address'), p.get('phone'))
                            st.session_state['final'] = code
                            st.success("Fait ! Voir Atelier.")
                with colB:
                    if st.button("📧 Email", key=f"e_{p.get('place_id')}"):
                        st.text_area("Email", generate_email_prospection(p.get('title'), q))

with tab2:
    st.header("🔧 Atelier")
    
    if 'final' in st.session_state:
        st.download_button("💾 TÉLÉCHARGER LE SITE", st.session_state['final'], "index.html", "text/html", use_container_width=True)
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
            else:
                st.warning("Aucune image trouvée dans le code HTML.")
        
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
