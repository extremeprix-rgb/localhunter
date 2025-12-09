import streamlit as st
import openai
from serpapi import GoogleSearch
import resend
import time
import re
import base64
import hashlib

st.set_page_config(page_title="LocalHunter V15 (Final)", page_icon="📍", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #0f172a; color: white; border-radius: 8px; font-weight: 600; }
    .badge-none { background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #ef4444; }
    .badge-weak { background-color: #ffedd5; color: #9a3412; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #f97316; }
    .badge-ok { background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
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

# --- MOTEUR DE SCAN V15 (GPS LOCK) ---

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
    
    # Variable pour stocker la "Zone Géographique" (ll parameter)
    gps_context = None 

    for page in range(max_pages):
        start_index = page * 20
        status_container.info(f"⏳ Scan Page {page + 1}/{max_pages}...")
        
        # Paramètres de base
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
        
        # Si on a trouvé le GPS à la page 1, on l'injecte pour les pages suivantes
        if gps_context and page > 0:
            params["ll"] = gps_context
        
        try:
            client_search = GoogleSearch(params)
            data = client_search.get_dict()
            
            # Gestion erreurs API
            if "error" in data:
                st.warning(f"Note SerpApi (Page {page+1}) : {data['error']}")
                if "Missing location" in data['error']:
                    st.error("⚠️ Impossible de paginer sans coordonnées GPS. Précisez la ville (ex: 'Lyon France').")
                break
            
            # Extraction du GPS pour les pages suivantes (seulement au premier tour)
            if page == 0:
                try:
                    meta_url = data.get("search_metadata", {}).get("google_maps_url", "")
                    match = re.search(r'@([-0-9.]+),([-0-9.]+),([0-9.]+)z', meta_url)
                    if match:
                        gps_context = f"@{match.group(1)},{match.group(2)},{match.group(3)}z"
                except:
                    pass

            local_results = data.get("local_results", [])
            
            if not local_results:
                break 
            
            for res in local_results:
                pid = res.get("place_id", str(hash(res.get("title"))))
                if pid not in seen_ids:
                    res["site_quality"] = check_site_quality(res.get("website"))
                    all_results.append(res)
                    seen_ids.add(pid)
            
            time.sleep(2) # Pause anti-blocage
            
        except Exception as e:
            st.error(f"Erreur technique : {e}")
            break
            
    status_container.success(f"✅ Scan Terminé : {len(all_results)} résultats trouvés.")
    time.sleep(2)
    status_container.empty()
    
    # TRI
    order = {"NONE": 0, "WEAK": 1, "OK": 2}
    all_results.sort(key=lambda x: order[x["site
