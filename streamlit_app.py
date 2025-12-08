import streamlit as st
import base64
import re
import time

st.set_page_config(page_title="LocalHunter V11 (Base64)", page_icon="🏆", layout="wide")

# CSS
st.markdown("""
<style>
    div.stButton > button:first-child { 
        background-color: #000000; 
        color: white; 
        border-radius: 6px; 
        font-weight: 600; 
    }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS ---

def image_to_base64(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        bytes_data = uploaded_file.getvalue()
        b64_str = base64.b64encode(bytes_data).decode()
        mime = "image/png" if uploaded_file.name.lower().endswith(".png") else "image/jpeg"
        return f"data:{mime};base64,{b64_str}"
    except Exception as e:
        st.error(f"Erreur: {e}")
        return None

def surgical_image_replace(html_content, base64_image):
    if not base64_image or not html_content:
        return html_content
    # Regex pour trouver <img ... src="..."> ou src='...'
    # On capture le début, le contenu du src, et la fin
    pattern = r'(<img[^>]+src=["\'])([^"\']*)(["\'][^>]*>)'
    
    # On remplace UNIQUEMENT la première image trouvée (l'image Hero généralement)
    if re.search(pattern, html_content, re.IGNORECASE):
        new_html = re.sub(pattern, fr'\1{base64_image}\3', html_content, count=1, flags=re.IGNORECASE)
        return new_html
    return html_content

def config_email(html_content, email):
    if not email: return html_content
    # Remplace l'action du form
    pattern = r'action=["\']https://formsubmit\.co/[^"\']*["\']'
    replacement = f'action="https://formsubmit.co/{email}"'
    if re.search(pattern, html_content):
        return re.sub(pattern, replacement, html_content)
    # Fallback si action n'existe pas
    return html_content.replace('<form', f'<form action="https://formsubmit.co/{email}"')

def generate_mock_html(job, city, phone):
    # Utilisation de LoremFlickr pour une image valide dès le départ
    img_url = f"https://loremflickr.com/1200/800/{job.replace(' ', ',')}?random={int(time.time())}"
    
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro {job} - {city}</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-gray-50 text-gray-800">
    <nav class="bg-white shadow p-4">
        <div class="container mx-auto font-bold text-xl text-blue-900">{job} Expert</div>
    </nav>
    <header class="relative h-96 flex items-center justify-center bg-gray-900">
        <img src="{img_url}" class="absolute inset-0 w-full h-full object-cover opacity-60" alt="{job}">
        <div class="relative z-10 text-center text-white p-4">
            <h1 class="text-4xl font-bold mb-2">{job} à {city}</h1>
            <a href="tel:{phone}" class="mt-4 inline-block bg-blue-600 text-white px-6 py-2 rounded font-bold">📞 {phone}</a>
        </div>
    </header>
    <section class="py-12 container mx-auto px-4 text-center">
        <h2 class="text-2xl font-bold mb-4">Contact</h2>
        <form action="https://formsubmit.co/votre-email@gmail.com" method="POST" class="max-w-md mx-auto space-y-4">
            <input type="text" name="nom" placeholder="Votre Nom" class="w-full border p-2 rounded" required>
            <input type="tel" name="tel" placeholder="Votre Téléphone" class="w-full border p-2 rounded" required>
            <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded font-bold">Envoyer</button>
        </form>
    </section>
</body>
</html>"""

# --- UI ---
st.title("🏆 LocalHunter V11 (Base64)")

tab1, tab2 = st.tabs(["CHASSE", "ATELIER"])

with tab1:
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1: job = st.text_input("Activité", "Plombier")
    with c2: city = st.text_input("Ville", "Lyon")
    with c3: 
        st.write("")
        if st.button("SCAN"):
            st.success("3 Prospects trouvés (Simulation)")
            st.session_state['last_scan'] = {'job': job, 'city': city}

    if 'last_scan' in st.session_state:
        s = st.session_state['last_scan']
        with st.expander(f"📍 {s['job']} Express ({s['city']})"):
            if st.button("⚡ Générer Site"):
                code = generate_mock_html(s['job'], s['city'], "06 01 02 03 04")
                st.session_state['generated_html'] = code
                st.experimental_rerun()
        
        if 'generated_html' in st.session_state:
            st.text_area("Code HTML", st.session_state['generated_html'], height=150)
            st.info("Copiez ce code ou allez dans l'Atelier.")

with tab2:
    st.header("🔧 Atelier Customisation")
    
    # 1. INPUT HTML
    html_in = st.text_area("Collez le code HTML ici :", value=st.session_state.get('generated_html', ''), height=200)
    
    if html_in:
        c_img, c_mail = st.columns(2)
        
        # 2. IMAGE
        with c_img:
            st.subheader("🖼️ Image Base64")
            up_img = st.file_uploader("Image Client (JPG/PNG)", type=['png', 'jpg', 'jpeg'])
            if up_img and st.button("Fusionner Image"):
                b64 = image_to_base64(up_img)
                if b64:
                    html_in = surgical_image_replace(html_in, b64)
                    st.session_state['generated_html'] = html_in
                    st.success("Image fusionnée !")
                    st.experimental_rerun()
        
        # 3. EMAIL
        with c_mail:
            st.subheader("📧 Email")
            email = st.text_input("Email Client")
            if email and st.button("Configurer Email"):
                html_in = config_email(html_in, email)
                st.session_state['generated_html'] = html_in
                st.success("Email configuré !")
                st.experimental_rerun()

        st.divider()
        st.download_button("💾 TÉLÉCHARGER index.html", html_in, "index.html", "text/html")
        st.components.v1.html(html_in, height=500, scrolling=True)
