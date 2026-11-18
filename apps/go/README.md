# Salubri Go (PWA)

Application mobile du citoyen : photo + GPS + type de déchets, **fonctionne hors ligne** (outbox IndexedDB, envoi automatique au retour du réseau, envoi idempotent via `client_id`), liste des dépotoirs autour de soi.

- Servie par nginx sous `/go/` (build : `pnpm --filter go build`, fait automatiquement par l'image Docker `web`).
- **Application Android (Capacitor)** : même code, embarqué dans un APK avec les modèles de masquage. Au premier lancement l'écran « Adresse du serveur Salubri » demande l'adresse de l'ordinateur (`192.168.x.x`, bouton « Tester » = `GET /api/health`) ; « Changer de serveur » en bas de l'écran. Les appels API passent par `CapacitorHttp` (http:// sur le réseau local accepté ; seules les adresses 10.x, 172.16-31.x, 192.168.x et localhost sont acceptées). APK de débogage : artefact `salubri-go-apk` du workflow « Android », ou en local (Node, JDK 21 — celui d'Android Studio convient —, SDK Android ; pas besoin de pnpm global) :
  ```
  npx -y pnpm@9.12.0 install --frozen-lockfile      # à la racine du dépôt
  cd apps/go
  set SALUBRI_NATIVE=1                               # PowerShell : $env:SALUBRI_NATIVE="1"
  npx -y pnpm@9.12.0 exec vite build                 # → dist/native
  npx -y pnpm@9.12.0 exec cap sync android
  cd android && gradlew.bat assembleDebug            # fichier local.properties : sdk.dir=C:/Users/<vous>/AppData/Local/Android/Sdk
  ```
  Résultat : `apps/go/android/app/build/outputs/apk/debug/app-debug.apk` (installation : « sources inconnues »).
- **Guide vocal** (pour les personnes qui ne lisent pas) : au lancement, après la synchronisation, une voix française dit « Si vous parlez français, appuyez ici » puis une voix mooré fait de même ; le bouton de la langue qui parle brille. Le signalement se fait ensuite pas à pas, un grand bouton par étape : photo (la caméra s'ouvre) → quantité (la voix cite chaque option, le bouton correspondant brille) → type de déchet → localisation (demandée seulement si elle n'est pas déjà autorisée) → remerciement, avec « transmis » ou « enregistré, sera transmis » selon le réseau. La voix répète le choix touché ; sans son autorisé par le navigateur, un message invite à toucher l'écran. « Continuer sans voix » (écran de langue) et « Écrire à la main » (étape position) ramènent au formulaire classique ; l'icône de langue de l'en-tête permet de changer de langue. Code : `src/voice/` (script des phrases, lecteur, séquences, écrans). Les voix sont des MP3 dans `public/audio/<fr|mos>/` (mis en cache hors ligne) : français généré par `scripts/go_audio_fr.py` (kokoro-onnx), mooré enregistré en une prise (`scripts/audio_src/mos_enregistrement.opus`) puis découpé en 22 fichiers par `scripts/go_audio_mos_decoupe.py` ; liste et textes : [`docs/AUDIO_GO.md`](../../docs/AUDIO_GO.md) ; un fichier absent ne bloque rien (les boutons brillent sans son).
- Dev : `pnpm --filter go dev` → http://localhost:5174/go/ (API relayée vers `localhost:8000` : pile lancée avec `docker-compose.dev.yml`).
- **GPS sur téléphone** : les navigateurs n'autorisent la géolocalisation qu'en HTTPS (ou sur `localhost`). Sur le réseau local en HTTP, la position se saisit à la main (signalement « à revoir » par la mairie).
