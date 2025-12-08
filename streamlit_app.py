<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LocalHunter V11 - Base64 (Images Incassables)</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .tab-btn.active { border-bottom: 2px solid #2563eb; color: #2563eb; }
        .st-btn { background-color: #000000; color: white; border-radius: 6px; font-weight: 600; transition: opacity 0.2s; }
        .st-btn:hover { opacity: 0.8; }
        iframe { border: 1px solid #e5e7eb; border-radius: 0.5rem; }
    </style>
</head>
<body class="bg-gray-50 text-gray-800 font-sans min-h-screen">

    <div class="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        <!-- Header -->
        <header class="mb-8">
            <h1 class="text-3xl font-bold flex items-center gap-2">
                <span class="text-4xl">🏆</span> LocalHunter V11 (Images Incassables)
            </h1>
            <p class="text-gray-500 mt-2">Générez des sites one-page et fusionnez les images en Base64 pour éviter les liens cassés.</p>
        </header>

        <!-- Tabs Navigation -->
        <div class="border-b border-gray-200 mb-6">
            <nav class="-mb-px flex space-x-8">
                <button onclick="switchTab('chasse')" id="btn-chasse" class="tab-btn active whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm">
                    CHASSE
                </button>
                <button onclick="switchTab('atelier')" id="btn-atelier" class="tab-btn whitespace-nowrap py-4 px-1 border-b-2 border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300">
                    ATELIER (Customisation)
                </button>
            </nav>
        </div>

        <!-- TAB 1: CHASSE -->
        <div id="tab-chasse" class="tab-content active">
            <div class="bg-white rounded-lg shadow p-6 mb-6">
                <div class="grid grid-cols-1 md:grid-cols-6 gap-4 items-end">
                    <div class="md:col-span-2">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Activité</label>
                        <input type="text" id="hunt-job" value="Maçon" class="w-full rounded-md border-gray-300 shadow-sm border p-2 focus:ring-blue-500 focus:border-blue-500" placeholder="ex: Maçon">
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Ville</label>
                        <input type="text" id="hunt-city" value="Bordeaux" class="w-full rounded-md border-gray-300 shadow-sm border p-2 focus:ring-blue-500 focus:border-blue-500" placeholder="ex: Bordeaux">
                    </div>
                    <div class="md:col-span-1">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Pages</label>
                        <input type="number" id="hunt-pages" value="1" min="1" max="5" class="w-full rounded-md border-gray-300 shadow-sm border p-2 focus:ring-blue-500 focus:border-blue-500">
                    </div>
                    <div class="md:col-span-1">
                        <button onclick="runScan()" class="st-btn w-full py-2 px-4 shadow-sm text-sm">
                            SCAN
                        </button>
                    </div>
                </div>
            </div>

            <!-- Status Box -->
            <div id="scan-status" class="hidden rounded-md bg-blue-50 p-4 mb-6">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <i class="fas fa-info-circle text-blue-400"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-blue-800" id="status-text">Prêt à scanner</h3>
                    </div>
                </div>
            </div>

            <!-- Results Area -->
            <div id="results-container" class="space-y-4">
                <!-- Prospects will be injected here -->
            </div>
        </div>

        <!-- TAB 2: ATELIER -->
        <div id="tab-atelier" class="tab-content">
            <div class="mb-6">
                <h2 class="text-xl font-bold text-gray-900 mb-4">🔧 Customisation Pro</h2>
                
                <!-- Step 1: Upload HTML -->
                <div class="bg-white rounded-lg shadow p-6 mb-6 border-l-4 border-blue-500">
                    <h3 class="font-semibold text-lg mb-2">1. Charger le fichier HTML</h3>
                    <p class="text-sm text-gray-500 mb-4">Chargez un fichier .html existant ou collez le code généré dans l'onglet Chasse.</p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Fichier HTML</label>
                            <input type="file" id="html-upload" accept=".html" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" onchange="handleHtmlUpload()">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Ou coller le code HTML</label>
                            <textarea id="html-content" rows="4" class="w-full rounded-md border-gray-300 shadow-sm border p-2 font-mono text-xs" placeholder="<!DOCTYPE html>..."></textarea>
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- Step 2: Image Injection -->
                    <div class="bg-white rounded-lg shadow p-6 border-l-4 border-purple-500">
                        <h3 class="font-semibold text-lg mb-2 flex items-center gap-2">🖼️ Insérer Image Client</h3>
                        <div class="bg-blue-50 text-blue-800 p-3 rounded text-sm mb-4">
                            <strong>Solution "Base64" :</strong> L'image sera transformée en texte et injectée directement DANS le fichier. Plus aucun lien cassé !
                        </div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Charger la photo (JPG/PNG)</label>
                        <input type="file" id="image-upload" accept="image/png, image/jpeg, image/jpg" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100 mb-4">
                        
                        <button onclick="fusionImage()" class="st-btn w-full py-2 px-4 shadow-sm text-sm">
                            Fusionner Image & Code
                        </button>
                    </div>

                    <!-- Step 3: Email Config -->
                    <div class="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
                        <h3 class="font-semibold text-lg mb-2 flex items-center gap-2">📧 Email Formulaire</h3>
                        <div class="mb-4">
                            <label class="block text-sm font-medium text-gray-700 mb-1">Email du client</label>
                            <input type="email" id="client-email" class="w-full rounded-md border-gray-300 shadow-sm border p-2" placeholder="client@exemple.com">
                        </div>
                        <button onclick="configEmail()" class="st-btn w-full py-2 px-4 shadow-sm text-sm">
                            Configurer Email
                        </button>
                    </div>
                </div>
            </div>

            <!-- Final Result Area -->
            <div id="final-area" class="hidden">
                <div class="relative py-4">
                    <div class="absolute inset-0 flex items-center" aria-hidden="true">
                        <div class="w-full border-t border-gray-300"></div>
                    </div>
                    <div class="relative flex justify-center">
                        <span class="bg-gray-50 px-2 text-sm text-gray-500">RÉSULTAT</span>
                    </div>
                </div>

                <div class="bg-green-50 rounded-lg p-4 mb-4 border border-green-200">
                    <div class="flex items-center justify-between">
                        <div>
                            <h3 class="text-lg font-medium text-green-800">🎉 FICHIER FINAL (Prêt à envoyer)</h3>
                            <p class="text-green-600 text-sm">L'image est maintenant intégrée dans le code.</p>
                        </div>
                        <button onclick="downloadHtml()" class="bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-md font-medium shadow-sm flex items-center gap-2">
                            <i class="fas fa-download"></i> Télécharger index.html
                        </button>
                    </div>
                </div>

                <div class="mb-2">
                    <label class="text-sm font-medium text-gray-700">Code HTML Final</label>
                    <textarea id="final-code" readonly class="w-full h-32 rounded-md border-gray-300 shadow-sm border p-2 font-mono text-xs mt-1 bg-gray-50"></textarea>
                </div>

                <div class="mt-4">
                    <label class="text-sm font-medium text-gray-700 mb-2 block">Aperçu Final</label>
                    <iframe id="preview-frame" class="w-full h-[500px] bg-white shadow-sm"></iframe>
                </div>
            </div>
        </div>

    </div>

    <!-- JAVASCRIPT LOGIC -->
    <script>
        // --- Tab Management ---
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => {
                el.classList.remove('active');
                el.classList.remove('text-blue-600');
                el.classList.remove('border-blue-600');
                el.classList.add('border-transparent');
                el.classList.add('text-gray-500');
            });

            document.getElementById('tab-' + tabId).classList.add('active');
            const btn = document.getElementById('btn-' + tabId);
            btn.classList.add('active');
            btn.classList.remove('border-transparent');
            btn.classList.remove('text-gray-500');
            btn.classList.add('text-blue-600');
            btn.classList.add('border-blue-600');
        }

        // --- Mock Data & Scan Logic (Tab 1) ---
        function runScan() {
            const job = document.getElementById('hunt-job').value;
            const city = document.getElementById('hunt-city').value;
            const statusBox = document.getElementById('scan-status');
            const statusText = document.getElementById('status-text');
            const resultsContainer = document.getElementById('results-container');

            if(!job || !city) {
                alert("Veuillez remplir l'activité et la ville.");
                return;
            }

            // Simulate loading
            statusBox.classList.remove('hidden');
            statusBox.className = "rounded-md bg-blue-50 p-4 mb-6";
            statusText.textContent = `📍 Scan de ${city} pour "${job}"...`;
            resultsContainer.innerHTML = '';

            setTimeout(() => {
                // Mock results
                const mockResults = [
                    { id: 1, title: `${job} Express`, address: `12 Rue de la Liberté, ${city}`, phone: "05 56 00 00 01" },
                    { id: 2, title: `Atelier ${job} ${city}`, address: `45 Avenue Jean Jaurès, ${city}`, phone: "06 12 34 56 78" },
                    { id: 3, title: `${job} Pro Services`, address: `8 Impasse des Lilas, ${city}`, phone: "07 98 76 54 32" }
                ];

                statusBox.className = "rounded-md bg-green-50 p-4 mb-6";
                statusBox.innerHTML = `<div class="flex"><div class="flex-shrink-0"><i class="fas fa-check-circle text-green-400"></i></div><div class="ml-3"><h3 class="text-sm font-medium text-green-800">✅ ${mockResults.length} résultats trouvés (Simulation).</h3></div></div>`;

                // Render results
                mockResults.forEach(res => {
                    const el = document.createElement('div');
                    el.className = "bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow";
                    el.innerHTML = `
                        <div class="flex flex-col md:flex-row justify-between gap-4">
                            <div class="flex-1">
                                <h3 class="text-lg font-bold text-gray-900">📍 ${res.title}</h3>
                                <p class="text-gray-500 text-sm">${res.address}</p>
                                <p class="text-gray-400 text-xs mt-1">Tel: ${res.phone}</p>
                            </div>
                            <div class="flex gap-2 items-start">
                                <button onclick="generateSite(${res.id}, '${res.title.replace(/'/g, "\\'")}', '${job}', '${city}', '${res.address.replace(/'/g, "\\'")}', '${res.phone}')" class="st-btn px-3 py-1 text-sm bg-gray-800 text-white rounded">⚡ Site</button>
                                <button onclick="generateEmail('${res.title.replace(/'/g, "\\'")}')" class="st-btn px-3 py-1 text-sm bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded">📧 Email</button>
                            </div>
                        </div>
                        <div id="output-${res.id}" class="mt-4 hidden">
                            <!-- Generated content goes here -->
                        </div>
                    `;
                    resultsContainer.appendChild(el);
                });

            }, 1000);
        }

        // --- Generation Logic (Mock AI) ---
        function generateSite(id, name, job, city, addr, phone) {
            const container = document.getElementById(`output-${id}`);
            container.classList.remove('hidden');
            
            // Fix broken links: Use Placehold.co as reliable fallback if LoremFlickr fails
            // Adding onerror handler to the img tag itself for robustness
            const imgUrl = `https://loremflickr.com/1200/800/${encodeURIComponent(job)}?random=${Date.now()}`;
            const fallbackUrl = `https://placehold.co/1200x800?text=${encodeURIComponent(job)}`;

            const template = `<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${name} - ${job} à ${city}</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-gray-50 font-sans">
    <nav class="bg-white shadow-sm py-4">
        <div class="container mx-auto px-6 flex justify-between items-center">
            <h1 class="text-xl font-bold text-blue-900">${name}</h1>
            <a href="#contact" class="bg-blue-600 text-white px-4 py-2 rounded-md font-semibold hover:bg-blue-700">Devis Gratuit</a>
        </div>
    </nav>

    <!-- Hero Section -->
    <header class="relative h-96 flex items-center justify-center bg-gray-900">
        <!-- L'image est configurée avec un fallback automatique si le lien est brisé -->
        <img src="${imgUrl}" onerror="this.src='${fallbackUrl}'" class="absolute inset-0 w-full h-full object-cover opacity-60" alt="${job}">
        <div class="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-80"></div>
        <div class="relative z-10 text-center text-white px-4">
            <h2 class="text-4xl md:text-5xl font-bold mb-4">Votre Expert ${job} à ${city}</h2>
            <p class="text-xl mb-8">Service professionnel et qualité garantie.</p>
            <a href="tel:${phone}" class="bg-white text-blue-900 px-6 py-3 rounded-lg font-bold hover:bg-gray-100 transition">📞 ${phone}</a>
        </div>
    </header>

    <!-- Services -->
    <section class="py-16 bg-white">
        <div class="container mx-auto px-6 text-center">
            <h3 class="text-3xl font-bold text-gray-900 mb-12">Nos Services</h3>
            <div class="grid md:grid-cols-3 gap-8">
                <div class="p-6 border rounded-lg hover:shadow-lg transition">
                    <div class="text-4xl mb-4">🏠</div>
                    <h4 class="text-xl font-bold mb-2">Rénovation</h4>
                    <p class="text-gray-600">Remise à neuf de vos espaces avec soin.</p>
                </div>
                <div class="p-6 border rounded-lg hover:shadow-lg transition">
                    <div class="text-4xl mb-4">🛠️</div>
                    <h4 class="text-xl font-bold mb-2">Dépannage</h4>
                    <p class="text-gray-600">Intervention rapide en cas d'urgence.</p>
                </div>
                <div class="p-6 border rounded-lg hover:shadow-lg transition">
                    <div class="text-4xl mb-4">📐</div>
                    <h4 class="text-xl font-bold mb-2">Conseil</h4>
                    <p class="text-gray-600">Expertise technique pour vos projets.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Contact -->
    <section id="contact" class="py-16 bg-gray-100">
        <div class="container mx-auto px-6 max-w-lg">
            <h3 class="text-3xl font-bold text-center mb-8">Contactez-nous</h3>
            <div class="bg-white p-8 rounded-lg shadow-md">
                <p class="mb-6 text-center text-gray-600">Adresse : ${addr}<br>Tel : ${phone}</p>
                
                <form action="https://formsubmit.co/votre-email@gmail.com" method="POST" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Nom</label>
                        <input type="text" name="name" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Téléphone</label>
                        <input type="tel" name="phone" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm border p-2">
                    </div>
                    <button type="submit" class="w-full bg-blue-600 text-white py-2 px-4 rounded-md font-bold hover:bg-blue-700">Envoyer ma demande</button>
                </form>
            </div>
        </div>
    </section>

    <footer class="bg-gray-900 text-white py-8 text-center">
        <p>&copy; 2024 ${name}. Tous droits réservés.</p>
    </footer>
</body>
</html>`;

            container.innerHTML = `
                <div class="mb-2 flex justify-between items-center">
                    <span class="text-xs font-semibold uppercase text-gray-500">Code HTML Généré</span>
                    <button onclick="copyToClipboard('code-${id}')" class="text-xs text-blue-600 hover:underline">Copier</button>
                </div>
                <textarea id="code-${id}" class="w-full h-48 font-mono text-xs border rounded p-2 bg-gray-50" readonly>${template}</textarea>
                <div class="mt-2 text-right">
                    <button onclick="sendToAtelier('code-${id}')" class="text-sm bg-purple-600 text-white px-3 py-1 rounded hover:bg-purple-700">🛠️ Envoyer vers l'Atelier</button>
                </div>
            `;
        }

        function generateEmail(name) {
            alert(`Fonctionnalité Email pour ${name} non implémentée dans cette démo.`);
        }

        function copyToClipboard(elementId) {
            const el = document.getElementById(elementId);
            el.select();
            navigator.clipboard.writeText(el.value).then(() => {
                alert("Code copié !");
            });
        }

        function sendToAtelier(elementId) {
            const code = document.getElementById(elementId).value;
            document.getElementById('html-content').value = code;
            switchTab('atelier');
            window.scrollTo(0,0);
        }

        // --- Atelier Logic (Tab 2) ---

        // 1. Handle HTML Upload
        function handleHtmlUpload() {
            const fileInput = document.getElementById('html-upload');
            const file = fileInput.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('html-content').value = e.target.result;
                    alert("Fichier HTML chargé !");
                };
                reader.readAsText(file);
            }
        }

        // 2. Fusion Image (Base64) - CORE FEATURE
        function fusionImage() {
            const htmlContent = document.getElementById('html-content').value;
            const fileInput = document.getElementById('image-upload');
            
            if (!htmlContent) {
                alert("Erreur: Veuillez d'abord charger ou coller du code HTML.");
                return;
            }
            if (!fileInput.files || !fileInput.files[0]) {
                alert("Erreur: Veuillez sélectionner une image (JPG/PNG).");
                return;
            }

            const file = fileInput.files[0];
            const reader = new FileReader();

            reader.onload = function(e) {
                const base64Data = e.target.result; // Format: "data:image/png;base64,..."
                
                // Regex robuste: cherche <img ... src="..." ...>
                // Fonctionne avec " ou '
                const regex = /(<img[^>]+src=["'])([^"']*)(["'][^>]*>)/i;
                
                if (!regex.test(htmlContent)) {
                    alert("Impossible de trouver une balise <img> dans le code. Assurez-vous qu'il y a bien une image à remplacer.");
                    return;
                }

                // Remplacement chirurgical
                const newHtml = htmlContent.replace(regex, `$1${base64Data}$3`);
                
                document.getElementById('html-content').value = newHtml;
                updateFinalPreview(newHtml);
                alert("✅ Image fusionnée en Base64 avec succès !");
            };

            reader.readAsDataURL(file);
        }

        // 3. Config Email
        function configEmail() {
            let htmlContent = document.getElementById('html-content').value;
            const email = document.getElementById('client-email').value;

            if (!email || !email.includes('@')) {
                alert("Email invalide.");
                return;
            }

            // Regex for FormSubmit action
            const regex = /action=["']https:\/\/formsubmit\.co\/[^"']*["']/;

            if (!regex.test(htmlContent)) {
                // Tentative d'injection si l'attribut action n'existe pas
                 if(htmlContent.includes('<form')) {
                    const confirmReplace = confirm("Lien FormSubmit non trouvé. Voulez-vous configurer le premier formulaire trouvé ?");
                    if(confirmReplace) {
                         htmlContent = htmlContent.replace(/<form[^>]*>/, (match) => {
                             if(match.includes('action=')) {
                                 return match.replace(/action=["'][^"']*["']/, `action="https://formsubmit.co/${email}"`);
                             } else {
                                 return match.replace('<form', `<form action="https://formsubmit.co/${email}"`);
                             }
                         });
                    } else {
                        return;
                    }
                 } else {
                     alert("Aucune balise <form> trouvée.");
                     return;
                 }
            } else {
                htmlContent = htmlContent.replace(regex, `action="https://formsubmit.co/${email}"`);
            }

            document.getElementById('html-content').value = htmlContent;
            updateFinalPreview(htmlContent);
            alert("Email configuré !");
        }

        function updateFinalPreview(html) {
            document.getElementById('final-area').classList.remove('hidden');
            document.getElementById('final-code').value = html;
            
            const iframe = document.getElementById('preview-frame');
            iframe.srcdoc = html;
        }

        function downloadHtml() {
            const html = document.getElementById('final-code').value;
            if(!html) { alert("Rien à télécharger."); return; }
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'index.html';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

    </script>
</body>
</html>
