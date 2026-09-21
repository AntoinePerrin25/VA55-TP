# TP1 — prise en main EV3

## Purpose

Code Pybricks MicroPython du robot EV3 (moteurs, puis capteurs, LCD, logs).

## Open this module when

Changer le déplacement, les ports, les capteurs, le son, les LEDs ou les évènements.

## Ownership

Possède le pilotage, les capteurs, le son/LEDs, les évènements, l’état, l’écran, les logs et la démo.

## Behavior and interactions

`forward(speed)` avance (`mm/s`). `drive(speed, turn_rate)` pour le PID. `rotate(angle, aSpeed)` tourne sur place. `stop()` arrête. Positif = avance / gauche.

`CapteurDistance.distance()` renvoie la distance en mm. Sans `sensor_type`, le brick essaie l’ultrason puis l’IR.

`CapteurCouleur.refresh()` lit la réflexion une fois (LED rouge, 0–100). `zone()` / `sur_ligne()` / `reflection()` réutilisent cet échantillon. `color()` seulement hors boucle (cycle R/G/B, pas de blanc).

`SonLumiere.allumer(couleur)` / `eteindre()` / `clignoter()` via `ev3.light` (les deux LEDs ensemble). `beep()` pour le son.

`Evenements.update()` compare zone et distance à l’échantillon précédent. `on("zone", fn)` reçoit `(avant, maintenant)`. `on("proximite", fn)` reçoit la distance au franchissement du seuil.

`Demo` boucle à 100 ms. PID latéral plus réactif en courbure (`Kp`, `δ` max). Vitesse de croisière constante sur la ligne ; rampe accélération/freinage **seulement** pour un obstacle (`SLOW_MM` → `STOP_MM`, reprise à `REPRISE_MM`).

## Entry points

- [`tp1/pilotage.py`](tp1/pilotage.py) — classe `Pilotage`
- [`tp1/capteur_distance.py`](tp1/capteur_distance.py) — classe `CapteurDistance`
- [`tp1/capteur_couleur.py`](tp1/capteur_couleur.py) — classe `CapteurCouleur`
- [`tp1/son_lumiere.py`](tp1/son_lumiere.py) — classe `SonLumiere`
- [`tp1/evenements.py`](tp1/evenements.py) — classe `Evenements`
- [`tp1/RobotState.py`](tp1/RobotState.py) — classe `RobotState`
- [`tp1/RobotLCD.py`](tp1/RobotLCD.py) — classe `LCD`
- [`tp1/RobotLogger.py`](tp1/RobotLogger.py) — classe `RobotLogger`
- [`tp1/demo.py`](tp1/demo.py) — classe `Demo`
- [`tp1/test.py`](tp1/test.py) — affichage de la version Python

## Change map

| To change... | Start with... | Verify with... |
| --- | --- | --- |
| Avancer / tourner / s’arrêter | `Pilotage` dans `tp1/pilotage.py` | `brickrun -r -- pybricks-micropython /home/robot/tp1/pilotage.py` |
| Ports B/C ou polarité | `__init__` de `Pilotage` | Un `forward(200)` d’1 s : le robot doit aller tout droit |
| Distance IR / ultrason | `CapteurDistance` dans `tp1/capteur_distance.py` | `brickrun -r -- pybricks-micropython /home/robot/tp1/capteur_distance.py` |
| Couleur / zones au sol | `CapteurCouleur` dans `tp1/capteur_couleur.py` | `brickrun -r -- pybricks-micropython /home/robot/tp1/capteur_couleur.py` |
| Son / LEDs | `SonLumiere` dans `tp1/son_lumiere.py` | `brickrun -r -- pybricks-micropython /home/robot/tp1/son_lumiere.py` |
| Changement de zone / proximité | `Evenements` dans `tp1/evenements.py` | `brickrun -r -- pybricks-micropython /home/robot/tp1/evenements.py` |
| Boucle / PID / bang-bang | `Demo` dans `tp1/demo.py` (`commande`, `commande_bangbang`, `vitesse`) | `brickrun -r -- pybricks-micropython /home/robot/tp1/demo.py` |
| État / LCD / CSV | `RobotState`, `LCD`, `RobotLogger` | Écran + `log_pid.csv` pendant `demo.py` |

## Dependencies

Pybricks `Motor`, `DriveBase`, `UltrasonicSensor`, `InfraredSensor`, `ColorSensor`, `EV3Brick`. Ports : B gauche, C droit, 2 distance, 3 couleur.

## Invariants and hazards

Python 3.4 sur le brick : pas de f-strings. Lancer avec `brickrun`, pas `./fichier.py`. `forward` / `drive` sont en **mm/s**. Diamètre et entraxe (`WHEEL_DIAMETER`, `AXLE_TRACK`) doivent matcher le châssis. L’IR convertit 0–100 vers 0–700 mm. Recaler `CONSIGNE`, `KP`/`KI`/`KD`, `SPEED`, `SLOW_MM`/`STOP_MM` sur le tapis. PID via `drive()`. `refresh()` couleur et distance une fois par `pas()`. Obstacle : rampe puis stop, reprise si l’obstacle part. Bouton central pour arrêter. CSV `log_pid.csv`. Excel FR : `;`. Depuis le Mac : `scp robot@IP:/home/robot/tp1/log_pid.csv .`
