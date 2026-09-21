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
TAU = DT / 1000.0
CONSIGNE = 50
LOG_CSV = "log_pid.csv"
LCD_TOUS_LES = 5

# Bang-bang (rapport)
DELTA = 30

# PID — virages réactifs. Rampe vitesse = obstacles seulement.
SPEED = 155
DELTA_MAX = 95
MAX_DDELTA = 48
KP = 1.6
KI = 1.15
KI_BLANC = 1.45
KD = 0.09
DE_ALPHA = 0.5

# Rampe uniquement si obstacle (mm/s par tick)
ACCEL_PAS = 35
DECEL_PAS = 70

# Obstacle
SLOW_MM = 450
STOP_MM = 110
REPRISE_MM = 160
PROXIMITE_MM = STOP_MM


class Demo(object):
    """Boucle 100 ms : PID latéral lissé + rampe / stop obstacle."""

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
        self._sum_e = 0
        self._e_prev = None
        self._de_f = 0
        self._delta_prev = 0
        self._v = 0
        self._arrete = False
        self._reprise = False
        self._n = 0

    def _sur_zone(self, avant, maintenant):
        print("zone {0} -> {1}".format(avant, maintenant))
        if self._arrete:
            return
        if maintenant == "ligne":
            self.io.allumer(Color.GREEN)
        else:
            self.io.allumer(Color.ORANGE)

    def _sur_proximite(self, dist):
        print("obstacle {0} mm".format(dist))
        self.io.allumer(Color.RED)
        self.io.beep(200, 120)

    def commande_bangbang(self, e):
        if e < 0:
            return -DELTA
        return DELTA

    def _facteur_obstacle(self, dist):
        if dist <= STOP_MM:
            return 0.0
        if dist >= SLOW_MM:
            return 1.0
        return float(dist - STOP_MM) / float(SLOW_MM - STOP_MM)

    def _cible_vitesse(self, dist):
        if self._arrete:
            if dist >= REPRISE_MM:
                self._arrete = False
                self.io.allumer(Color.GREEN)
            else:
                return 0.0
        if dist <= STOP_MM:
            self._arrete = True
            return 0.0
        return SPEED * self._facteur_obstacle(dist)

    def _appliquer_rampe(self, cible):
        dv = cible - self._v
        if dv > ACCEL_PAS:
            dv = ACCEL_PAS
        elif dv < -DECEL_PAS:
            dv = -DECEL_PAS
        self._v += dv
        if self._v < 0:
            self._v = 0
        if self._v > SPEED:
            self._v = SPEED
        return self._v

    def _rampe_obstacle(self, cible):
        if cible < SPEED:
            self._reprise = True
            return self._appliquer_rampe(cible)
        if self._reprise and self._v < SPEED:
            v = self._appliquer_rampe(SPEED)
            if v >= SPEED:
                self._reprise = False
            return v
        self._v = SPEED
        self._reprise = False
        return SPEED

    def _limite_delta(self, delta):
        d = delta - self._delta_prev
        if d > MAX_DDELTA:
            delta = self._delta_prev + MAX_DDELTA
        elif d < -MAX_DDELTA:
            delta = self._delta_prev - MAX_DDELTA
        self._delta_prev = delta
        return delta

    def commande(self, e):
        p = KP * e

        if self._e_prev is not None and e * self._e_prev < 0:
            self._sum_e = self._sum_e * 0.2

        ki = KI_BLANC if e > 0 else KI
        self._sum_e += e
        i = ki * TAU * self._sum_e
        if i > DELTA_MAX:
            i = DELTA_MAX
            if ki * TAU != 0:
                self._sum_e = DELTA_MAX / (ki * TAU)
        elif i < -DELTA_MAX:
            i = -DELTA_MAX
            if ki * TAU != 0:
                self._sum_e = -DELTA_MAX / (ki * TAU)

        if self._e_prev is None:
            de = 0
        else:
            de = e - self._e_prev
        self._de_f = DE_ALPHA * de + (1.0 - DE_ALPHA) * self._de_f
        d = (KD / TAU) * self._de_f
        self._e_prev = e

        delta = p + i + d
        if delta > DELTA_MAX:
            delta = DELTA_MAX
        elif delta < -DELTA_MAX:
            delta = -DELTA_MAX
        return self._limite_delta(delta)

    def pas(self):
        self.refl = self.couleur.refresh()
        self.dist = self.distance.refresh()
        self.events.update()
        self.erreur = self.refl - CONSIGNE
        cible = self._cible_vitesse(self.dist)
        speed = self._rampe_obstacle(cible)
        if speed < 8:
            self.pilotage.stop()
            delta = 0
        else:
            delta = self.commande(self.erreur)
            self.pilotage.drive(speed, delta)
        zone = self.couleur.zone()
        self.etat.update(
            zone,
            self.dist,
            self.refl,
            self.erreur,
            zone,
            delta,
            speed,
        )
        self.etat.log()
        if self._n % LCD_TOUS_LES == 0:
            self.etat.status()
        self._n += 1

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
