# Alex Management — Video Cleaner Bot

Bot Telegram qui strip et remplace les métadonnées des vidéos via FFmpeg.

## Déploiement sur Railway

### 1. Upload le code
- Crée un repo GitHub avec ces 4 fichiers
- Sur Railway : New Project → Deploy from GitHub repo

### 2. Ajoute la variable d'environnement
Dans Railway → ton projet → Variables :
```
BOT_TOKEN = ton_token_telegram
```

### 3. C'est tout
Railway détecte nixpacks.toml, installe FFmpeg + Python automatiquement.

---

## Utilisation par les VAs

1. Ouvrir le bot @aleksgls_bot
2. /start → choisir un preset (iPhone, Samsung, CapCut, DaVinci)
3. Envoyer la vidéo via 📎 **Fichier** (pas "Vidéo") pour garder la qualité
4. Recevoir la vidéo nettoyée en retour

## Presets disponibles
- iPhone 15 Pro
- Samsung Galaxy S24
- CapCut 5.2
- DaVinci Resolve 18
- Personnalisé (device + encoder + auteur)
