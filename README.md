# CS2 TradeUp Finder 🚀

Ce projet est un outil industriel de détection d'opportunités de **Trade-Ups CS2** (contrats d'échange), spécialisé dans les **mélanges 1/9 (Mix Mode)**. Il intègre une couche d'intelligence artificielle pour assainir les prix et se protéger des manipulations de marché.

---

## 🏗️ Architecture du Projet

Le projet suit une structure modulaire pour séparer la logique métier de l'exécution :

```text
tradeupfinder/
├── tradeup/             # PACKAGE CORE
│   ├── config.py        # Centralisation de TOUS les paramètres (FEE, ROI, etc.)
│   ├── database.py      # Gestion de la persistance SQLite et du schéma
│   ├── sanitizer.py     # IA de prix : Prédictions hybrides et détection d'anomalies
│   ├── scanner.py       # Moteur de recherche : Algorithme de scan 1/9
│   └── utils.py         # Parsing des noms Buff et calculs de floats
├── scripts/             # POINTS D'ENTRÉE TÂCHES
│   ├── update_db.py     # Sync JSON -> DB et exécution de la Sanitization
│   └── scan_mixes.py    # Logique de lancement du scanner
├── data/                # PERSISTANCE DES DONNÉES
│   ├── cs2_skins.db     # Base de données structurée
│   ├── price.json       # Export brut du marché (Buff)
│   └── manual_overrides.json # Forçage manuel des prix par l'utilisateur
├── reports/             # OUTPUTS & ANALYSE
│   └── mix_results.json # Top opportunités du dernier scan
├── main.py              # Interface CLI de pilotage unique
└── [Docs].md            # Documentation métier détaillée (Sanitizer, Floats)
```

---

## 🧠 Les Piliers du Système

### 1. Le Pipeline de Données (Anti-Manipulation)
La donnée brute (`price.json`) est souvent polluée par des prix "fake". Notre pipeline traite l'information en 3 étapes :
- **Import** : Transformation des noms Buff en entités typées (Skin, Condition, StatTrak).
- **Sanitization** : Le `PriceSanitizer` calcule un **Predicted Price** basé sur la rareté du float et les stats de collection.
- **Flagging** : Si `Prix Réel > 5x Prix Prédit` ou si la courbe est inversée (FT > MW), l'item est marqué comme **Irregular**.
- **Usage** : Le scanner utilise les prix réels pour vos **Dépenses** (vos coûts) mais les prix prédits pour vos **Gains** (ce que l'item vaut vraiment).

### 2. Le Moteur de Scan 1/9 (Mix Mode)
L'algorithme cherche à maximiser le rendement en combinant :
- **1 Target** : Un item haut de gamme d'une collection rentable.
- **9 Fillers** : Des items peu coûteux d'autres collections.
- **Probabilités** : Le système applique strictement la loi des 10%/90% pour le calcul de l'EV (Expected Value).
- **Gestion des Floats** : Le scanner calcule automatiquement le float requis sur les fillers pour garantir la qualité de sortie (ex: forcer un FN en sortie). Il intègre un calcul de surcoût (Premium) pour les fillers à très bas float.

### 3. Analyse de Liquidité et Ratios
Le projet inclut un outil de génération de rapport (`FLOAT_RATIO_REРORT.md`) qui analyse :
- **Buckets de Float** : L'impact de la précision du float (0.01 vs 0.05) sur le prix de vente.
- **Ratio d'augmentation** : Multiplicateur de prix par rapport au prix de base.
- **Liquidité réelle** : Nombre de ventes par bucket pour éviter les items invendables.

---

## 🛠️ Commandes CLI

Tout se pilote via le point d'entrée `main.py` :

| Commande | Action |
| :--- | :--- |
| `python3 main.py update` | Met à jour la DB, lance l'IA de prix et détecte les anomalies. |
| `python3 main.py scan` | Lance la recherche d'opportunités de trade-ups (Mix 1/9). |

---

## ⚙️ Paramétrage Rapide (`tradeup/config.py`)

- **`FEE`** : Actuellement `0.95` (5% de frais de revente cumulés).
- **`MIN_ROI`** : Seuil minimal pour afficher un contrat (par défaut `10.0%`).
- **`RMB_TO_USD_RATE`** : Taux de conversion utilisé pour uniformiser les calculs.

---

## 📖 Documentations Annexes
- [Logique du Sanitizer](SANITIZER_LOGIC.md) : Détail des algorithmes mathématiques de l'IA.
- [Rapport de Ratios](FLOAT_RATIO_REРORT.md) : Analyse de la valeur des floats précis.

---
*Ce projet est maintenu sous une structure modulaire permettant l'ajout facile de nouveaux modes de trade-up (ex: 5/5).*
