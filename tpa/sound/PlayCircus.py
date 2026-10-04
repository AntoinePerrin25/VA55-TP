#!/usr/bin/env pybricks-micropython

from RobotState import RobotState

_script = __file__
_slash = _script.rfind("/")
_dir = _script[:_slash] if _slash >= 0 else "."


def _exists(path):
    try:
        handle = open(path)
    except OSError:
        return False
    handle.close()
    return True


TONES = _dir + "/thk.tones"
if not _exists(TONES):
    TONES = _dir + "/sound/thk.tones"

if __name__ == "__main__":
    robot = RobotState()
    robot.updateLCD("circus")
    robot.sound.play(TONES)
    robot.updateLCD("fin")
