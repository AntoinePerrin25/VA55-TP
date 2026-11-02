# MQTT — intersection du huit

## Purpose

Simuler deux robots sur le huit et laisser Node-RED accorder le croisement, sans le brick.

## Open this module when

Changer le feu, les topics MQTT, les zones d'arrêt, ou la vue du circuit.

## Ownership

Ce module possède le circuit rejoué, la simulation et le flux Node-RED. Il ne possède pas l'asservissement du brick (`tpa/`) : odométrie, gyro et Kalman y restent. La ligne suivie ici est la commande du premier tour de `trajectoire_2.csv`, refermée sur le départ (écart 90 mm). Le Kalman de ce tour reste ouvert de 288 mm, il ne sert pas de géométrie.

## Behavior and interactions

Deux robots suivent le même huit, dans le même sens. A et B partent à 200 mm/s, décalés d'un demi-tour. Le bouton de la vue en ajoute d'autres, avec leur propre consigne, sur le plus grand intervalle libre. Chacun publie `robots/{id}/state` (QoS 0).

Le capteur regarde celui de devant, jusqu'à 800 mm le long du circuit. La garde est de 280 mm : un robot plus rapide ralentit et s'aligne, il ne comble pas cet écart. Le disque de conflit fait 220 mm. Tant qu'il est vide, la voie est libre. Dès qu'un robot y entre, les autres s'arrêtent avant le disque de stockage (480 mm).

Node-RED publie `intersection/phase` (QoS 1, retenu) : `open`, `occupied` ou `all_red`. Le brick dans `tpa/` s'abonne au même message et publie `robots/{id}/state`. La vue `http://127.0.0.1:8765` dessine l'unique trajectoire, le trait du capteur et le feu.

## Entry points

| Fichier | Rôle |
| --- | --- |
| `circuit.py` | Découpe le huit et les abscisses d'arrêt |
| `simulate.py` | Robots, client MQTT, page |
| `intersection-flow.json` | Flux importé dans Node-RED |
| `mosquitto.conf` | Broker local, port 1883, anonyme |
| `view.html` | Dessin du circuit |

## Change map

| To change... | Start with... | Verify with... |
| --- | --- | --- |
| Qui a le droit d'entrer | `_step` dans `simulate.py` et le nœud « voie libre » | un robot arrêté repart dès que l'autre quitte `conflit` |
| Rayons des zones | `circuit.py` | la vue, un seul trait, deux passages au centre |
| Topics | `simulate.py` et `intersection-flow.json` | `mosquitto_sub -t 'intersection/phase' -v` |

## Dependencies

Mosquitto sur `127.0.0.1:1883`, Node-RED sur `127.0.0.1:1880`, `paho-mqtt` dans `.venv`. Le broker actuel n'écoute que la machine locale.

## Invariants and hazards

Un robot dont le disque est vide ne doit pas rester à l'arrêt : `_step` ne bloque que si un autre robot est déjà dans `conflit`. Les deux passages du huit sont le même croisement physique. La modulation de vitesse, pour ne plus s'arrêter du tout, n'est pas dans ce flux.
