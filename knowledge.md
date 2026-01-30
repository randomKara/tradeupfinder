
# 🎓 Le Guide Ultime du Marché CS2 : Stratégie, Mathématiques et Prestige

## 1. Les Bases : La Hiérarchie de la Valeur
Un skin est une apparence cosmétique dont la valeur repose sur trois piliers :
*   **La Rareté :** Du bleu (Mil-Spec) au rouge (Covert).
*   **La Collection :** L'origine du skin (certaines collections ne tombent plus, créant une rareté historique).
*   **L'Usure (Le Float) :** Une valeur de **0.00 (neuf)** à **1.00 (détruit)**. Elle détermine la "propreté" visuelle et la catégorie (Factory New, Minimal Wear, Field-Tested, Well-Worn, Battle-Scarred).

---

## 2. Skins Finaux vs Skins de Consommation
C'est ici que le marché devient complexe. Tous les skins d'une même rareté ne se valent pas.
*   **Le Skin de Consommation :** C'est un skin "moche" ou sur une arme peu jouée (ex: SCAR-20, G3SG1, Negev). Sa valeur est indexée uniquement sur son utilité comme **ingrédient** pour un contrat d'échange.
*   **Le Skin Final (Prestige) :** C'est la cible ultime. Ce sont des skins iconiques (AWP Asiimov, AK-47 Case Hardened, M4A4 Poseidon) sur des armes très jouées.
    *   **Le Point d'Arrêt :** Un Skin Final n'est jamais utilisé pour un trade-up. Il sort du circuit de consommation pour rejoindre l'inventaire d'un joueur ou d'un collectionneur.
    *   **L'Effet d'Aspiration :** La demande massive pour un Skin Final "tire" le prix de tous les ingrédients nécessaires à sa fabrication.

---

## 3. La Mécanique du "Trade Up" (Contrat d'Échange)
Le jeu permet de sacrifier **10 skins** d'une rareté pour en obtenir **1 seul** de la rareté supérieure.
*   **La boucle est bouclée :** On utilise des skins de consommation bon marché pour essayer d'atteindre un **Skin Final** prestigieux.

---

## 4. La Révolution du "Float Ajusté"
Le jeu ne regarde pas le float brut (ex: 0.15) lors d'un échange, mais sa **position relative** dans la range du skin.
$$Float_{Ajusté} = \frac{Float_{Réel} - Min_{Skin}}{Max_{Skin} - Min_{Skin}}$$
Cette formule est le secret des pros : elle permet d'utiliser des skins de consommation très usés (Battle-Scarred) pour obtenir un skin de prestige "neuf" (Factory New), à condition que l'ingrédient ait un float ajusté très bas.

---

## 5. Les "Paliers de Prix" et les Anomalies de Float
À cause des Skins Finaux, le prix des ingrédients ne suit pas toujours une courbe logique.
*   **Le Palier de Condition :** Si pour obtenir un Skin Final prestigieux en "Minimal Wear", il faut que l'ingrédient ait un float inférieur à **0.52** (en plein milieu du Battle-Scarred), alors le prix de cet ingrédient va exploser exactement à 0.52.
*   **Conséquence :** On peut trouver des skins Battle-Scarred qui valent 10 fois le prix de base juste parce qu'ils sont la "clé mathématique" pour débloquer un Skin Final recherché.

---

## 6. La Psychologie des Prix (La Boîte Noire)
Le prix d'un skin évolue selon trois zones :
1.  **Zone de Silence (BS) :** Le prix est souvent stable (prix plancher).
2.  **Zone Linéaire (FT -> MW) :** Le prix grimpe car le skin devient "utilisable" visuellement.
3.  **Zone Exponentielle (Le FN) :** Sous **0.07**, le prix s'envole. Passer de 0.05 à 0.01 peut multiplier le prix par 9.

Pour maîtriser cela, nous avons créé une **IA "Boîte Noire"** qui :
*   Utilise 150 requêtes quotidiennes pour étalonner la courbe de surcote réelle.
*   Prédit le prix de n'importe quel float en combinant des règles linéaires (FT/MW) et un modèle exponentiel (FN).

---

## 7. L'Algorithme Final : L'IA Génétique
Pour dominer le marché, nous n'utilisons plus de calculs manuels. Nous utilisons un **Algorithme Génétique**.
*   **L'Évolution :** L'IA génère des milliers de combinaisons de skins (Mixte). Elle fait "muter" les contrats pour trouver le mélange parfait entre skins de consommation (pas chers) et skins cibles.
*   **L'Objectif :** Trouver la faille où le coût de 10 ingrédients (ajusté par notre boîte noire de prix) est inférieur à la probabilité de toucher le **Skin Final**.
