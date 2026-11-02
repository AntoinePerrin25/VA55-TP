# tpa — robot sur le huit

## Purpose

Faire suivre la ligne au brick, publier sa position Kalman, et obéir au feu du croisement ainsi qu'au capteur de distance.

## Open this module when

Changer le pilotage réel, l'identité MQTT, le centre du huit ou la garde du capteur.

## Ownership

Le suivi de ligne, l'odométrie et Kalman restent dans `RobotLineFollower` et `RobotState`. `RobotIntersection` décide seulement la vitesse envoyée aux moteurs. `intersection.py` porte cette décision sans le matériel, avec les mêmes rayons que `tp_mqtt`.

## Behavior and interactions

`RobotMain.py` lance le PID. Avant chaque commande, le capteur sur le port S2 mesure ce qu'il y a devant. Rien au-delà de 800 mm : la consigne du PID est inchangée. À 280 mm ou moins, le robot s'arrête. Entre les deux, la vitesse baisse.

Le centre du huit est `(183, -898)` mm dans le repère du départ, cap 0. À 480 mm ou moins, c'est la zone de stockage. À 220 mm ou moins, le robot publie `conflit` sur `robots/{id}/state` (QoS 0) et traverse. Il s'abonne à `intersection/phase` (QoS 1). `open` laisse passer. `occupied` ou `all_red` arrête avant le disque, sauf si l'identifiant est dans `green` ou si le robot est déjà dedans : il finit alors de sortir.

L'écran affiche l'identifiant, `libre`, `rouge`, `conflit`, `suivi` ou `sans mqtt`, puis la mesure du capteur. `MQTT_BROKER` dans `RobotMain.py` est l'IP de la machine Mosquitto. `ROBOT_ID` est une lettre différente sur chaque brick.

## Entry points

| Fichier | Rôle |
| --- | --- |
| `RobotMain.py` | Identité, broker, lancement |
| `intersection.py` | Zones, feu, échelle du capteur |
| `RobotIntersection.py` | MQTT, ultrason, écran |
| `capteur_distance.py` | Port S2, ultrason ou infrarouge |

## Change map

| To change... | Start with... | Verify with... |
| --- | --- | --- |
| Le droit d'entrer | `granted` dans `intersection.py` | `python3 intersection.py` |
| Le centre ou les rayons | les constantes de `intersection.py` | le même script, puis un passage réel au milieu du huit |
| L'IP ou la lettre | `RobotMain.py` | l'écran passe de `sans mqtt` à `libre` |

## Dependencies

Pybricks, `umqtt`, Mosquitto à l'adresse `MQTT_BROKER`. Le capteur de distance est en S2, le suiveur de ligne en S1, le gyro en S3.

## Invariants and hazards

Un robot qui a publié `conflit` doit pouvoir ressortir même si le feu passe au rouge pendant la traversée. Deux bricks avec le même `ROBOT_ID` se déconnectent l'un l'autre. Le départ doit être le même point que l'enregistrement, cap vers l'avant de la ligne, sinon le centre calculé ne tombe pas sur le croisement.
