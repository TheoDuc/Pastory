# Cahier de vérification — étape 9 bis

Deux volets : **l'identité visuelle** (rien ne doit avoir changé dans les chiffres) et **la
prédiction de l'évolution** (un calcul nouveau, refaisable à la main). Toutes les valeurs de ce
cahier sont fictives ([D-03](../decisions.md)).

---

## 1. L'identité visuelle ne change aucun chiffre

Pendant la session, chaque nombre de chaque écran (27 états : la couverture, les cinq périodes de
la synthèse et de l'annexe, les types d'actifs, les quatre rubriques de la diversification
repliées et dépliées, les frais) a été relevé avant la première modification, puis après chaque
série de retouches, et les deux relevés comparés écran par écran. Sur les données du
propriétaire comme sur l'export fictif des tests, **les chiffres du moteur sont identiques**. Les
seules différences sont des déplacements, tous expliqués :

- l'anneau des poches, remplacé par une barre, ne porte plus son total arrondi (« 1 234 € ») ni
  ses montants de placement ; le total exact reste écrit (« base … ») ;
- la couverture répète la période couverte, la dernière opération lue et le nombre de fichiers ;
- la date des cours apparaît à côté du titre de chaque chapitre **et** dans la bulle « d'où
  viennent ces chiffres ».

### À vérifier par toi, à l'écran

- [ ] La valeur des actifs, le gain, le TRI, le TWRR et le capital net investi de la synthèse
  sont ceux que tu connais.
- [ ] Les montants des poches, sous la barre, sont ceux d'avant.
- [ ] De nuit (bouton lune), tout se lit, et la bande des filtres se distingue du reste.
- [ ] « Peu fiable », au survol, dit que la période est trop courte.

---

## 2. La prédiction de l'évolution, sans aléa : le cas à la calculatrice

**Le cas :** 1 000 € au départ, **5 %** par an, **10 ans**, **100 €** versés à la fin de chaque
mois. Formules : [glossaire](../glossaire.md) §9.

**Étape 1 — le taux mensuel.** Douze mois au taux mensuel doivent faire une année à 5 % :

    g = 1,05^(1/12) = 1,004 074 123 8

Contrôle : `g¹²` = 1,05.

**Étape 2 — les premiers mois, à la main.** Chaque mois, `V ← V × g + 100` :

| Mois | Calcul | Valeur |
|---|---|---|
| 0 | départ | 1 000,00 € |
| 1 | 1 000,00 × 1,004 074 12 + 100 | 1 104,07 € |
| 2 | 1 104,07 × 1,004 074 12 + 100 | 1 208,57 € |
| 12 | (par la forme fermée ci-dessous, n = 12) | 2 277,26 € |

**Étape 3 — la forme fermée, sur 120 mois.**

    gⁿ = 1,05¹⁰ = 1,628 894 63
    ce que devient le départ :   1 000 × 1,628 894 63            =  1 628,89 €
    ce que deviennent les versements :
        100 × (1,628 894 63 − 1) / (1,004 074 12 − 1) = 100 × 154,363 16 = 15 436,32 €
    total                                                              = 17 065,21 €

**Ce que l'application affiche :** **17 065,21 €** en octobre 2036 (pour un départ en
octobre 2026) ; ce que tu auras versé : **13 000,00 €** (1 000 + 120 × 100) ; ce que le taux aura
ajouté : **+4 065,21 €**. Un test le garde (`tests/test_projection.py`).

- [ ] Refais l'étape 3 à la calculatrice (la touche puissance suffit).

## 3. Avec l'aléa : ce qui se vérifie, et ce qui ne se vérifie pas

Les 10 000 chemins ne se refont pas à la main. Ce qui se vérifie :

- **la graine est fixe** : sur le cas ci-dessus, choisir « 10 000 simulations » doit toujours
  donner, au centime près :

  | Quantile | 10 % | 25 % | Médiane | 75 % | 90 % |
  |---|---|---|---|---|---|
  | Montant atteint | 13 313,00 € | 14 983,43 € | 17 136,67 € | 19 673,44 € | 22 195,94 € |

- **la médiane est proche de la courbe sans aléa** (17 136,67 € contre 17 065,21 €) : le taux
  saisi est celui de la médiane ([D-105](../decisions.md)) ; l'écart vient des versements, qui
  grandissent chacun sur une durée différente ;
- **un taux de 0 %** donne un éventail nul : les cinq quantiles égalent la courbe sans aléa ;
- **plus le taux est élevé, plus l'éventail est large** : la volatilité vaut deux fois le taux.

- [ ] Choisis « 10 000 simulations » sur le cas ci-dessus et compare au tableau.
- [ ] Passe le taux de 4 % à 15 % : l'écart entre 10 % et 90 % doit s'élargir nettement.
