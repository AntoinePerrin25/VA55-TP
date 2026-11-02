# VA55

Code des TPs EV3 (Pybricks MicroPython, Python 3.4).

| Module | Owns | Open when | Guide |
| --- | --- | --- | --- |
| [`tp1/`](tp1/) | Robot EV3 (mouvement, capteurs, LCD, CSV) | Déplacement, boucle 100 ms, logs | [MODULE_GUIDE.md](MODULE_GUIDE.md) |
| [`tpa/`](tpa/) | Brick : ligne, Kalman, capteur, feu MQTT | Pilotage réel du huit | [MODULE_GUIDE.md](tpa/MODULE_GUIDE.md) |
| [`tp_mqtt/`](tp_mqtt/) | Simulation du huit, feu MQTT, flux Node-RED | Intersection, topics, vitesse au croisement | [MODULE_GUIDE.md](tp_mqtt/MODULE_GUIDE.md) |

Le brick exécute :

```bash
brickrun -r -- pybricks-micropython /home/robot/tpa/RobotMain.py
```

```bash
python3 plot_logs.py
```

Tous les `*.csv` → `pid_plots.html` (e, δ, temps de parcours, gains `#meta`).