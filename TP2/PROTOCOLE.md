# Protocole — tours et trajectoire

Poser le robot sur le bord de la ligne, au point de départ du huit, et ne plus toucher au gyro avant le lancement. Le capteur couleur reste en lumière rouge.

Sur le brick, depuis le dossier `tpa` :

```bash
brickrun -r -- pybricks-micropython RobotMain.py
```

Faire trois tours complets, sans ramasser le robot et sans appuyer sur un bouton en route. Le tour se marque tout seul quand le robot a fait le huit et que son cap revient vers le départ. L’écran passe à Tour 2, puis Tour 3. Après le troisième tour, appuyer sur **centre**. Le fichier `trajectoire.csv` est alors fermé, à côté du programme. S’il existe déjà, le suivant s’appelle `trajectoire_2.csv`.

Copier ce CSV sur le PC, à la racine du projet. Puis :

```bash
python3 plot_trajectoire.py trajectoire.csv
```

Ouvrir `TP2/figures/trajectoire.html`. Les quatre courbes sont la commande PID, les moteurs, le gyro avec la vitesse commandée, et Kalman. Le texte donne l’écart au départ en millimètres : c’est l’erreur de fermeture après les trois tours. `tours_kalman.png` superpose les tours marqués automatiquement. Ils doivent se recouvrir. S’ils s’écartent en éventail, refaire un essai après avoir ajusté `WHEEL_DIAMETER_MM` et `AXLE_TRACK_MM` dans `tpa/RobotMain.py` (56 mm et 114 mm au départ).
