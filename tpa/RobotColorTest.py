#!/usr/bin/env pybricks-micropython

from pybricks.ev3devices import ColorSensor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Button, Color, Port
from pybricks.tools import StopWatch, wait


SENSOR_PORT = Port.S3
RED_ORANGE_THRESHOLD = 70
SAMPLE_PERIOD_MS = 200


def color_name(color):
    if color == Color.RED:
        return "RED"
    if color == Color.ORANGE:
        return "ORANGE"
    if color == Color.BLACK:
        return "BLACK"
    if color == Color.WHITE:
        return "WHITE"
    if color == Color.YELLOW:
        return "YELLOW"
    if color == Color.GREEN:
        return "GREEN"
    if color == Color.BLUE:
        return "BLUE"
    if color == Color.BROWN:
        return "BROWN"
    return str(color)


def main():
    ev3 = EV3Brick()
    sensor = ColorSensor(SENSOR_PORT)
    watch = StopWatch()

    ev3.screen.clear()
    ev3.screen.print("Couleur capteur")
    ev3.screen.print("CENTER pour quitter")
    wait(1000)

    while Button.CENTER not in ev3.buttons.pressed():
        measured_color = sensor.color()
        reflection = sensor.reflection()
        red_high = measured_color == Color.RED and reflection >= RED_ORANGE_THRESHOLD

        ev3.screen.clear()
        ev3.screen.print("Raw: " + color_name(measured_color))
        ev3.screen.print("Ref: " + str(reflection) + "%")
        ev3.screen.print("Seuil: " + str(RED_ORANGE_THRESHOLD))
        ev3.screen.print("Orange?: " + ("OUI" if red_high else "NON"))
        print(
            "{0} ms | raw={1} | reflection={2} | orange_candidate={3}".format(
                watch.time(), color_name(measured_color), reflection, red_high
            )
        )
        wait(SAMPLE_PERIOD_MS)

    ev3.screen.clear()
    ev3.screen.print("Test termine")


if __name__ == "__main__":
    main()