# VA55

Code des TPs EV3 (Pybricks MicroPython, Python 3.4).

| Module | Owns | Open when | Guide |
| --- | --- | --- | --- |
| [`tp1/`](tp1/) | Robot EV3 (mouvement, capteurs, LCD, CSV) | Déplacement, boucle 100 ms, logs | [MODULE_GUIDE.md](MODULE_GUIDE.md) |

Le brick exécute les scripts avec :

```bash
brickrun -r -- pybricks-micropython /home/robot/tp1/pilotage.py
```

```bash
python3 plot_logs.py
```

Tous les `*.csv` → `pid_plots.html` (e, δ, temps de parcours, gains `#meta`).