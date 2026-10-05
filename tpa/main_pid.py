from pybricks.hubs import EV3Brick
from pybricks.parameters import Button, Port
from pybricks.tools import StopWatch, wait

from robot import Robot
from capteur_couleur import CapteurCouleur


VITESSE = 100
CONSIGNE = 50
PERIODE_MS = 100
DT = PERIODE_MS / 1000.0
MAX_ROTATION = 50
KP = 1.5
KI = 0.4
KD = 0.03
INTEGRALE_MAX = 100

FICHIER_LOG = "suivi_pid.csv"


def borner(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def attendre_demarrage(ev3):
    ev3.screen.clear()
    ev3.screen.print("Commande PID")
    ev3.screen.print("Bouton central")
    ev3.screen.print("pour demarrer")
    while Button.CENTER not in ev3.buttons.pressed():
        wait(10)
    while Button.CENTER in ev3.buttons.pressed():
        wait(10)


def main():
    robot = Robot()
    if not robot.ready:
        return

    capteur_couleur = CapteurCouleur()
    if capteur_couleur.sensor is None:
        print("Branche le capteur couleur sur S3.")
        return

    ev3 = EV3Brick()
    chrono = StopWatch()
    fichier = open(FICHIER_LOG, "w")
    fichier.write("temps_ms,reflection,error,steering\n")

    attendre_demarrage(ev3)
    chrono.reset()
    integrale = 0
    erreur_precedente = 0

    try:
        while Button.CENTER not in ev3.buttons.pressed():
            reflection = capteur_couleur.reflection()
            error = reflection - CONSIGNE
            # PID : P + accumulation + anticipation de la variation.
            integrale += error * DT
            integrale = borner(integrale, -INTEGRALE_MAX, INTEGRALE_MAX)
            derivee = (error - erreur_precedente) / DT
            erreur_precedente = error
            steering = KP * error + KI * integrale + KD * derivee
            steering = borner(steering, -MAX_ROTATION, MAX_ROTATION)
            robot.drive(VITESSE, steering)
            fichier.write("{0},{1},{2},{3}\n".format(
                chrono.time(), reflection, error, steering
            ))
            wait(PERIODE_MS)
    finally:
        robot.stop()
        fichier.close()
        ev3.screen.clear()
        ev3.screen.print("Commande PID")
        ev3.screen.print("terminee")


main()