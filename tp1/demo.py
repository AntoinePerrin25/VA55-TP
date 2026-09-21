#!/usr/bin/env pybricks-micropython

from pybricks.parameters import Button, Color
from pybricks.tools import wait

from capteur_couleur import CapteurCouleur
from capteur_distance import CapteurDistance
from evenements import PROXIMITE, ZONE, Evenements
from pilotage import Pilotage
from RobotState import RobotState
from son_lumiere import SonLumiere

DT = 100
SPEED = 100
CONSIGNE = 50
DELTA = 30
PROXIMITE_MM = 150
LOG_CSV = "log_bangbang.csv"


class Demo(object):
    """Boucle 100 ms : capteurs + drive(). Remplacer commande() par le PID ensuite."""

    def __init__(self):
        self.pilotage = Pilotage()
        self.couleur = CapteurCouleur()
        self.distance = CapteurDistance()
        self.io = SonLumiere()
        self.etat = RobotState(self.io.ev3, LOG_CSV)
        self.events = Evenements(self.couleur, self.distance, PROXIMITE_MM)
        self.events.on(ZONE, self._sur_zone)
        self.events.on(PROXIMITE, self._sur_proximite)
        self.stop_demande = False
        self.erreur = 0
        self.dist = 0
        self.refl = 0

    def _sur_zone(self, avant, maintenant):
        print("zone {0} -> {1}".format(avant, maintenant))
        if maintenant == "ligne":
            self.io.allumer(Color.GREEN)
        else:
            self.io.allumer(Color.ORANGE)

    def _sur_proximite(self, dist):
        print("proximite {0} mm".format(dist))
        self.io.allumer(Color.RED)
        self.io.beep(200, 150)
        self.stop_demande = True

    def commande(self, e):
        # Bang-bang. later PID : return kp*e (+ ki*sum + kd*de)
        if e < 0:
            return -DELTA
        return DELTA

    def pas(self):
        self.events.update()
        self.refl = self.couleur.reflection()
        self.dist = self.distance.distance()
        self.erreur = self.refl - CONSIGNE
        delta = self.commande(self.erreur)
        self.pilotage.drive(SPEED, delta)
        zone = self.couleur.zone()
        self.etat.update(
            zone,
            self.dist,
            self.refl,
            self.erreur,
            zone,
            delta,
        )
        self.etat.status()
        self.etat.log()

    def run(self):
        self.io.allumer(Color.GREEN)
        self.io.beep(700, 80)
        while not self.stop_demande:
            if Button.CENTER in self.io.ev3.buttons.pressed():
                break
            self.pas()
            wait(DT)
        self.pilotage.stop()
        self.io.allumer(Color.RED)


if __name__ == "__main__":
    Demo().run()
