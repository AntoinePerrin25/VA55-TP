# Audit du rapport de suivi de ligne

## Verdict

Le rapport initial contenait les trois courbes d'erreur, mais ne permettait pas de soutenir un 20/20 sur la compréhension : code réduit à du pseudocode, durée d'enregistrement confondue avec temps sur 1 m, comparaison de réglages différents, unités de la commande ambiguës et analyse du tapis trop favorable. La version corrigée explique ces écarts et présente les résultats conservés sans les modifier. Une note exacte ne peut pas être prédite sans barème.

La compréhension peut être bien défendue à l'oral. La conformité expérimentale reste incomplète, même avec de bonnes explications.

## Exigences du sujet

La page 6 du sujet VA55_A25_TP_1_2 (1).pdf précise : code de la commande latérale, justification des choix, erreur bang-bang, erreur et temps sur une droite de **1 m**, erreur et temps sur tapis. Les deux essais PID doivent utiliser la commande latérale définitive. La page 7 demande initialement un pas de 100 ms ; les pages 7–8 introduisent successivement P, PI et PID.

| Exigence | État après correction |
| --- | --- |
| Erreur bang-bang | Présente, 1194 points ; seuil réel 20 et amplitudes ±200 vérifiés |
| Erreur droite | Présente, mais issue de logsTP1/log_pid_STRAIGHT.csv, pas de logsPIDbetter |
| Repère et temps sur 1 m | Repère physique confirmé par les auteurs ; temps estimé à 1000/155 = 6,45 s, sans chronométrage indépendant du franchissement |
| Erreur tapis | Présente, 1063 points ; circuit 8 exclu |
| Temps tapis | Parcours complet déclaré par les auteurs, arrêt manuel ; log de 21,168 s, sans marqueur indépendant d'arrivée |
| Même commande définitive pour droite et tapis | Non : les gains et les bornes diffèrent |
| Code latéral | Extraits exacts de la source actuelle ajoutés ; source exécutée lors des essais non archivée |
| Justification | Rôle de P/I/D, discrétisation, filtrage, anti-windup, saturation et limites ajoutés |

## Provenance

- Bang-bang : `logsPIDbetter/bang_bang.csv`.
- Droite : `logsTP1/log_pid_STRAIGHT.csv` ; métadonnées KP=1.7, KI=0.9, KI_BLANC=1.1, KD=0.06, DELTA_MAX=50, SPEED=155 mm/s.
- Tapis : `logsPIDbetter/suivi_pid_tapis_spir.csv`. `suivi_pid_tapis.csv` est identique octet pour octet : ce n'est pas un deuxième essai.
- `logsPIDbetter/robot_log.csv` ne contient qu'un en-tête.
- Les fichiers `*_8_*` et `robot_log(1).csv` (localisation/Kalman) sont exclus.

Aucun CSV n'a été édité ou simulé. Une simulation pourrait illustrer un mécanisme, mais ne remplacerait ni une mesure sur 1 m, ni le log d'un meilleur essai non sauvegardé.

## Chiffres reproductibles

Statistiques arithmétiques sur tous les échantillons, démarrage inclus ; erreurs en points de réflexion.

| Indicateur | Bang-bang | Droite | Tapis |
| --- | ---: | ---: | ---: |
| Durée du log (s) | 20,761 | 17,960 | 21,168 |
| Pas médian (ms) | 17 | 50 | 20 |
| Erreur moyenne signée | -18,50 | -0,75 | -2,59 |
| MAE | 29,78 | 7,89 | 20,72 |
| RMSE | 33,20 | 11,56 | 24,42 |
| Maximum de l'erreur absolue | 45 | 42 | 45 |
| Points à la borne de la commande PID | sans objet | 23/342 | 1/1063 |

`audit_logs.py` recalcule ces valeurs et vérifie le seuil bang-bang et la reconstruction du PID. Les coefficients 2 / 1.70 / 0.035 restituent steering, après saturation à ±300, à la précision numérique près. Cette identité valide les coefficients de la somme enregistrée ; elle ne prouve pas une bonne trajectoire ou un optimum de réglage.

Le tapis conserve de grands écarts. Une moyenne signée proche de zéro ne signifie pas une faible erreur : les écarts positifs et négatifs se compensent. Les niveaux près du noir n'indiquent pas une position latérale précise ; un seul capteur ne permet pas de reconstruire la trajectoire.

Sur l'extrait 8,6–12,6 s, les valeurs efficaces des contributions P/I/D sont 33,5/37,0/2,7 ; sur l'ensemble, 48,8/41,7/13,7. D est faible dans l'extrait choisi, mais sa contribution globale est plus importante.

## Points de compréhension à pouvoir expliquer

1. La réflexion est un signal optique ; e=x−50 est exprimée en points de réflexion, pas en millimètres. 0 et 100 sont les extrêmes de l'échelle, pas des valeurs de calibration noir/blanc relevées pendant l'essai.
2. Le bang-bang bascule à x=20, soit e=−30, alors que le PID vise x=50. La comparaison n'a donc pas exactement la même consigne effective.
3. P seul a besoin d'une erreur non nulle pour fournir une correction non nulle dans un virage. I peut maintenir cette correction avec une erreur plus faible ; son accumulation peut ensuite causer un dépassement.
4. La borne ±100 porte sur J, l'état intégral en points·s. Avec ki=1,70, le terme I est borné à ±170, pas ±100. Le gel conditionnel de J empêche d'accentuer une saturation.
5. La dérivée divise par le Δt réel en secondes. Le filtre à 0,15 diminue le bruit mais ajoute du retard. Initialiser previous_error=0 peut produire un pic au départ : une amélioration possible serait d'utiliser la première lecture, sans prétendre l'avoir testée.
6. Une attente de 5 ms n'est pas une période de 5 ms : calcul, lectures, écritures et éventuelle localisation s'y ajoutent. Les intervalles sont variables ; le code actuel mesure Δt.
7. RobotDrive.drive utilise des vitesses moteur en degrés/s et une correction de 2δ. Ce n'est pas l'interface DriveBase.drive en mm/s et degrés de rotation du robot/s. Les unités de l'ancien log droite sont déclarées en degrés de rotation/s ; le code historique correspondant n'est pas archivé.
8. Les défauts actuels de RobotLineFollower sont 1 / 0.85 / 0.0175 et max_steering=300. Ils diffèrent du tapis enregistré et du bang-bang à ±200. Il faut distinguer source actuelle, métadonnées et coefficients retrouvés dans un log.
9. Une limite sur δ ne garantit pas que les vitesses des roues restent réalisables : v±2δ peut demander des valeurs trop élevées. Aucun log de vitesse moteur ne permet de valider ces consignes sur le tapis.
10. Un repère physique à 1 m a été confirmé par les auteurs. Le trait à 1000/155=6,45 s représente une estimation à vitesse constante, pas un instant de franchissement chronométré. La colonne Distance (mm) de l'ancien log n'est pas une distance parcourue monotone. Elle ne permet pas d'identifier le franchissement de 1 m.

## Vérification du fichier

Le JSON corrigé conserve le canevas 1920×1080, les polices et les liens vers les quatre figures. Il comporte 12 diapositives. Les nombres du rapport sont vérifiés par le script d'audit. Un aperçu HTML local sert à vérifier la géométrie et la lisibilité ; il ne remplace pas une ouverture/export dans Slidepix, dont le moteur Markdown peut présenter des différences.

## Observation complémentaire des auteurs

Les auteurs indiquent que réduire l’attente à `period_ms=5`, donc calculer la correction plus souvent, a résolu le problème de stabilité lors de leurs meilleurs essais. Les logs correspondants n’ont pas été conservés : il s’agit d’une observation de séance, pas d’une amélioration quantifiée à partir des CSV disponibles. Cette attente ne garantit pas une période réelle de 5 ms, car le reste de la boucle prend également du temps.
