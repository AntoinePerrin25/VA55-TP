#!/usr/bin/env pybricks-micropython

from pybricks.ev3devices import ColorSensor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Button, Port
from pybricks.tools import wait


SENSOR_PORT = Port.S3
SAMPLE_PERIOD_MS = 100
CAPTURE_TIME_MS = 3000
CALIBRATION_FILE = "color_calibration.csv"


def capture(sensor, label):
    values = []
    elapsed = 0
    ev3.screen.clear()
    ev3.screen.print(label + " : mesure...")
    while elapsed < CAPTURE_TIME_MS:
        red, green, blue = sensor.rgb()
        values.append((red, green, blue, (red + green + blue) / 3))
        wait(SAMPLE_PERIOD_MS)
        elapsed += SAMPLE_PERIOD_MS
    brightness = [value[3] for value in values]
    return (
        min(value[0] for value in values),
        max(value[0] for value in values),
        min(value[1] for value in values),
        max(value[1] for value in values),
        min(value[2] for value in values),
        max(value[2] for value in values),
        min(brightness),
        max(brightness),
        sum(brightness) / len(brightness),
        len(values),
    )


def write_result(label, result):
    red_min, red_max, green_min, green_max, blue_min, blue_max, brightness_min, brightness_max, brightness_average, count = result
    with open(CALIBRATION_FILE, "a") as calibration_file:
        calibration_file.write(
            "{0};{1};{2};{3};{4};{5};{6};{7};{8};{9};{10}\n".format(
                label, red_min, red_max, green_min, green_max, blue_min,
                blue_max, brightness_min, brightness_max, brightness_average,
                count,
            )
        )


def show_result(label, result):
    red_min, red_max, green_min, green_max, blue_min, blue_max, brightness_min, brightness_max, brightness_average, count = result
    ev3.screen.clear()
    ev3.screen.print(label + " " + str(count) + " pts")
    ev3.screen.print("Lum " + str(round(brightness_average, 1)))
    ev3.screen.print("R " + str(red_min) + "-" + str(red_max))
    ev3.screen.print("G " + str(green_min) + "-" + str(green_max))
    ev3.screen.print("B " + str(blue_min) + "-" + str(blue_max))
    print("{0}: R={1}-{2} G={3}-{4} B={5}-{6} lum={7}-{8} moy={9} points={10}".format(
        label, red_min, red_max, green_min, green_max, blue_min, blue_max,
        brightness_min, brightness_max, brightness_average, count
    ))


def wait_release():
    while ev3.buttons.pressed():
        wait(50)


def main():
    global ev3
    ev3 = EV3Brick()
    sensor = ColorSensor(SENSOR_PORT)
    captures = {}

    with open(CALIBRATION_FILE, "w") as calibration_file:
        calibration_file.write(
            "zone;red_min;red_max;green_min;green_max;blue_min;blue_max;"
            "luminosity_min;luminosity_max;luminosity_average;points\n"
        )

    ev3.screen.clear()
    ev3.screen.print("CALIBRATION BLANC")
    ev3.screen.print("UP orange")
    ev3.screen.print("RIGHT blanc")
    ev3.screen.print("DOWN noir")
    ev3.screen.print("LEFT fin")
    wait(1500)

    while True:
        red, green, blue = sensor.rgb()
        brightness = (red + green + blue) / 3
        ev3.screen.clear()
        ev3.screen.print("RGB " + str(red) + "," + str(green) + "," + str(blue))
        ev3.screen.print("Lum " + str(round(brightness, 1)))
        ev3.screen.print("UP orange RIGHT blanc")
        ev3.screen.print("DOWN noir LEFT fin")
        buttons = ev3.buttons.pressed()
        if Button.LEFT in buttons:
            wait_release()
            break
        label = None
        if Button.UP in buttons:
            label = "ORANGE"
        elif Button.RIGHT in buttons:
            label = "BLANC"
        elif Button.DOWN in buttons:
            label = "NOIR"
        if label is not None:
            wait_release()
            result = capture(sensor, label)
            captures[label] = result
            write_result(label, result)
            show_result(label, result)
            wait(1500)
        else:
            wait(SAMPLE_PERIOD_MS)

    ev3.screen.clear()
    if "ORANGE" in captures:
        result = captures["ORANGE"]
        brightness_min = result[6]
        brightness_max = result[7]
        proposed_min = max(0, brightness_min - 2)
        proposed_max = min(100, brightness_max + 2)
        ev3.screen.print("ORANGE lum: " + str(proposed_min) + "-" + str(proposed_max))
        print("MESURE BLANCHE: utiliser RGB, pas reflection()")
        print("LUMINOSITE ORANGE PROPOSEE: {0}-{1}".format(proposed_min, proposed_max))
    else:
        ev3.screen.print("Orange non mesure")
    ev3.screen.print("Voir " + CALIBRATION_FILE)
    print("Calibration terminee: " + CALIBRATION_FILE)


if __name__ == "__main__":
    main()