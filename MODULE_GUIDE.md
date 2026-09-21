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

`CapteurCouleur.color()` renvoie la `Color` Pybricks (LED R/G/B en cycle, pas de blanc). `zone()` / `sur_ligne()` utilisent la réflexion, LED rouge. `color()` seulement si on veut la couleur.

`SonLumiere.allumer(couleur)` / `eteindre()` / `clignoter()` via `ev3.light` (les deux LEDs ensemble). `beep()` pour le son.

`Evenements.update()` compare zone et distance à l’échantillon précédent. `on("zone", fn)` reçoit `(avant, maintenant)`. `on("proximite", fn)` reçoit la distance au franchissement du seuil.

`Demo` enchaîne tout dans une boucle 100 ms : bang-bang sur la réflexion, `RobotState` + LCD + CSV, stop proximité ou bouton central. Remplacer `commande()` par le PID.

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
| Boucle complète / bang-bang | `Demo` dans `tp1/demo.py` | `brickrun -r -- pybricks-micropython /home/robot/tp1/demo.py` |
| État / LCD / CSV | `RobotState`, `LCD`, `RobotLogger` | Écran + `log_bangbang.csv` pendant `demo.py` |

## Dependencies

Pybricks `Motor`, `DriveBase`, `UltrasonicSensor`, `InfraredSensor`, `ColorSensor`, `EV3Brick`. Ports : B gauche, C droit, 2 distance, 3 couleur.

## Invariants and hazards

Python 3.4 sur le brick : pas de f-strings. Lancer avec `brickrun`, pas `./fichier.py`. `forward` / `drive` sont en **mm/s**, plus en deg/s moteurs. Diamètre et entraxe (`WHEEL_DIAMETER`, `AXLE_TRACK`) doivent matcher le châssis ; si ça recule, inverser `Direction` du moteur gauche. L’IR n’est pas en mm natif : `distance()` convertit 0–100 vers 0–700 mm (`IR_MM_PER_UNIT`). Forcer le type avec `sensor_type='us'` ou `'ir'` si l’auto-détection se trompe. Recaler `LINE_REFLECTION_MAX`, `CONSIGNE` et `DEFAULT_ZONES` sur le tapis réel. Le PID doit appeler `drive()`, pas `rotate()` : brancher dans `Demo.commande()`. `ev3.light` allume les deux LEDs ensemble (`GREEN`, `RED`, `ORANGE`). `Evenements` ne déclenche rien tout seul : il faut `update()` dans la boucle. Premier échantillon ignoré. Proximité = front montant seulement (pas tant qu’on reste trop près). Bouton central pour arrêter la démo. Le CSV du rapport (`log_bangbang.csv`) est recréé à chaque `RobotState()`. Excel FR : séparateur `;`. Après un run : `scp robot@IP:/home/robot/tp1/log_bangbang.csv .`
