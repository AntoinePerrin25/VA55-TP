# TP MQTT · lancement

## 1. Sur le PC

Mettre le PC et les EV3 sur le même réseau. Les commandes se lancent depuis la racine du dépôt, avec Mosquitto, Node.js avec npm et Python 3.10 ou plus récent installés.

**Terminal 1 · broker local**

```sh
mosquitto -c tp_mqtt/mosquitto.conf
```

**Terminal 2 · contrôleur**

Installer Node-RED une seule fois.

```sh
npm install -g node-red
```

Puis lancer le contrôleur à chaque séance.

```sh
node-red
```

Ouvrir [l’éditeur Node-RED](http://127.0.0.1:1880), importer `tp_mqtt/intersection-flow.json` et cliquer sur **Déployer**. Le flux utilise le broker local sur le port `1883`.

**Terminal 3 · vue du huit**

Installer les dépendances la première fois.

```sh
python3 -m venv tp_mqtt/.venv
tp_mqtt/.venv/bin/pip install -r tp_mqtt/requirements.txt
```

Choisir une commande selon l’essai, puis ouvrir [la vue du huit](http://127.0.0.1:8765).

```sh
./tp_mqtt/run.sh            # essai sans EV3 : deux robots simulés
./tp_mqtt/run.sh --observe  # essai avec EV3 : affichage seul
```

## 2. Sur chaque EV3

Brancher le capteur de couleur en **S1**, la distance en **S2**, le gyro en **S3** et les moteurs en **B/C**. Avant de copier les scripts, régler [`tpa/RobotMain.py`](../tpa/RobotMain.py) pour le brick.

- `MQTT_BROKER` est l’IP du PC qui héberge Mosquitto. `MQTT_PORT` vaut `1883` par défaut.
- `ROBOT_ID` est propre au robot, par exemple `A` ou `B`.
- `START_POSE` donne la pose au départ dans le repère du tracé TP2, en mm et degrés. Pour partir vers la gauche depuis le milieu du haut du huit, utiliser `(0, 0, 180)`. Sur l’EV3 A, `INVERT_POSE_Y = True` corrige le signe de Y et du cap local avant la rotation vers le repère du tapis.

Depuis le PC, remplacer `IP_EV3` par l’adresse du brick et copier les scripts.

```bash
ssh robot@10.37.135.215 'mkdir -p /home/robot/tpa'
scp tpa/Robot{Main,State,Drive,Sensor,LCD,Logger,LineFollower,Intersection}.py \
    tpa/{intersection,capteur_distance}.py robot@10.37.135.215:/home/robot/tpa/
ssh robot@10.37.135.215
```

Depuis la session SSH sur l’EV3, lancer le programme.

```sh
cd /home/robot/tpa
brickrun -r -- pybricks-micropython RobotMain.py
```

Le bouton central arrête le robot. Commencer avec un seul EV3 pour vérifier sa position dans la vue et son point d’arrêt sur le tapis.

## 3. Rejoindre le broker commun aux groupes

1. Mettre les PC et les EV3 sur le réseau du TP. Récupérer l’adresse et le port du broker commun. Le code actuel utilise MQTT sur TCP, sans nom d’utilisateur, mot de passe ni TLS.
2. Sur chaque EV3, régler `MQTT_BROKER` et `MQTT_PORT` dans `RobotMain.py`, puis recopier ce fichier et relancer le programme. Choisir un `ROBOT_ID` unique parmi **tous** les groupes, par exemple `G2_A`. Le contrôleur accepte les lettres majuscules, les chiffres, `_` et `-`, sur 16 caractères maximum. Aligner aussi les poses de départ sur le même repère si les robots partagent le tapis.
3. Pour le croisement commun, **un seul contrôleur** doit publier sur `intersection/phase`. Si votre groupe assure ce rôle avec Node-RED, ouvrir le nœud **états robots**, éditer le serveur MQTT **Mosquitto local**, renseigner l’adresse et le port communs, puis déployer. Les nœuds d’entrée et de sortie utilisent le même serveur. Si un contrôleur est déjà en place, rejoindre le broker comme robot ou observateur. Pour que les EV3 acceptent ses phases, il doit publier `mode: acces_cooperatif` et une liste `green` contenant au plus un identifiant.
4. Sur le PC, remplacer `IP_BROKER_COMMUN` et `1883` par les valeurs données en séance pour afficher la vue ou suivre les messages MQTT.

```sh
./tp_mqtt/run.sh --observe --broker IP_BROKER_COMMUN --port 1883
mosquitto_sub -h IP_BROKER_COMMUN -p 1883 -t 'robots/+/state' -t intersection/phase -q 1 -v
```

[Rapport Slidepix](rapport.slidepix.json)
