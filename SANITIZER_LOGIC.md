# Documentation du PriceSanitizer 🧠

Le **PriceSanitizer** est le moteur d'intelligence de prix du projet. Son rôle est de transformer les prix bruts du marché (souvent bruités ou manipulés) en "prix prédits" réalistes pour garantir la fiabilité des calculs de rentabilité.

---

## 🛠 Les Méthodes de Prédiction

L'IA utilise un modèle hybride combinant deux approches complémentaires.

### 1. Méthode Statistique (Collection-Based)
Cette méthode part du principe que dans une même collection et pour une même rareté, les skins partagent une base de valeur commune.
- **Groupement** : Réunit tous les skins par `(Collection, Rareté, StatTrak)`.
- **Calcul** : Calcule la **médiane** et l'**écart-type** de ce groupe.
- **Avantage** : Très robuste contre un item unique dont le prix s'envole, car elle le ramène à la normale de sa collection.

### 2. Méthode de Régression Non-Linéaire (Exponential Decay) 📉
Cette méthode modélise la valeur en fonction de la "rareté du float" à l'aide d'une régression exponentielle entraînée sur les données réelles du marché.
- **Formule** : $Ratio = 1 + \alpha e^{-k \times Adj\_Float}$
- **Entraînement** : Les paramètres $\alpha$ (intensité) et $k$ (vitesse de décroissance) sont calculés périodiquement par le script `scripts/train_model.py` et sauvegardés dans `data/model_params.json`.
- **Calcul de prédiction** : 
  $Prix_{cible} = Prix_{base} \times \frac{1 + \alpha e^{-k \times Adj\_Target}}{1 + \alpha e^{-k \times Adj\_Base}}$
- **Avantage** : Capture beaucoup mieux la courbe de valeur réelle (très forte hausse pour les floats proches de 0) par rapport à un modèle linéaire simple.

### 3. Modèle Hybride
Le prix final prédit est une moyenne pondérée :
`Prix_Final = (0.6 * Stats_Collection) + (0.4 * Regression_Float)`

---

## 🔍 Détection des Anomalies

Le Sanitizer analyse chaque prix réel par rapport à sa prédiction et applique des filtres de sécurité.

### 1. Le Filtre de "Manipulation" (Inverted Curve) 🛡️
C'est la protection la plus efficace contre les arnaques au trade-up. 
- **Règle** : Si une condition inférieure est significativement plus chère qu'une condition supérieure (ex: un **StatTrak FT** à $80 alors que le **StatTrak MW** vaut $30).
- **Action** : L'item est immédiatement marqué comme `irregular = 1` et le scanner utilisera le prix prédit ($~25) à la place.

### 2. Le Filtre de Ratio (Outlier)
- **Seuil** : Si le prix réel est **5 fois supérieur** (ou inférieur) au prix prédit par l'IA.
- **Cas d'usage** : Détecte les items "collector" ou les erreurs de listing massives.

### 3. Le Filtre Sigma
- **Seuil** : Utilise l'écart-type de la collection. Si un item s'éloigne de plus de **2.5 sigmas** de la médiane, il est suspecté d'être une anomalie.

---

## 🎮 Forçage Manuel (`manual_overrides.json`)

L'IA ne peut pas tout savoir (ex: un skin avec un pattern très rare comme Case Hardened Blue Gem). 
Vous pouvez court-circuiter l'IA en utilisant le fichier `data/manual_overrides.json` :

```json
[
  {
    "skin": "Nova | Rising Skull",
    "condition": "FT",
    "is_stattrak": true,
    "price": 15.0,
    "comment": "L'IA le surestimaient à cause d'un manque de samples"
  }
]
```
**Priorité :** `Manuel > Prédit > Réel` (si irrégulier).

---

## 📊 Impact sur le Scanner

Lorsqu'un item est marqué `is_irregular` dans la base de données :
1. **En Entrée (Target)** : Le scanner utilise votre prix d'achat réel (car c'est votre coût).
2. **En Sortie (Outcomes)** : Le scanner ignore le prix du marché et utilise le **Prix Prédit**.
   - *Cela évite de croire qu'on va gagner $200 sur un contrat alors que le skin de sortie est invendable à ce prix.*

---
*Document technique - Système de Protection Anti-Manipulation*
