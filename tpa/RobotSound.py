from pybricks.tools import wait

MIN_BEEP_HZ = 100
MAX_BEEP_HZ = 10000
MAX_BEEP_MS = 400
MAX_REST_MS = 500


class RobotSound:
    """Play tones on the EV3 speaker.

    The brick plays one tone at a time with ``speaker.beep()``. Convert the
    file on a computer first. MIDI keeps the melody only:

        python3 sound/prepare_midi.py sound/circus.mid

    MP3 is converted the same way with ``prepare_mp3.py``. Both write a
    ``.tones`` file (frequency in Hz, duration in ms). A frequency of 0 is
    silence, because ``beep()`` plays anything under 100 Hz as 100 Hz.
    """

    def __init__(self, ev3, volume=100):
        self.speaker = ev3.speaker
        self.set_volume(volume)

    def set_volume(self, volume):
        self.volume = volume
        self.speaker.set_volume(volume, "_all_")

    def beep(self, frequency=500, duration=100):
        self.speaker.beep(frequency, duration)

    def play_notes(self, notes, tempo=120):
        self.speaker.play_notes(notes, tempo)

    def play_file(self, file_name):
        self.speaker.play_file(file_name)

    def play_tones(self, path):
        with open(path) as tones:
            for line in tones:
                frequency, duration = _parse_tone(line)
                if duration <= 0:
                    continue
                if frequency < MIN_BEEP_HZ:
                    if duration > MAX_REST_MS:
                        duration = MAX_REST_MS
                    wait(duration)
                    continue
                if frequency > MAX_BEEP_HZ:
                    frequency = MAX_BEEP_HZ
                if duration > MAX_BEEP_MS:
                    duration = MAX_BEEP_MS
                self.speaker.beep(frequency, duration)

    def play(self, path):
        if _ends_with(path, ".wav"):
            self.play_file(path)
            return
        if _ends_with(path, ".tones"):
            self.play_tones(path)
            return
        if _ends_with(path, ".mp3") or _ends_with(path, ".mid"):
            self.play_tones(path[:-4] + ".tones")
            return
        raise ValueError("unsupported sound file: " + path)


def _ends_with(path, suffix):
    if len(path) < len(suffix):
        return False
    return path[-len(suffix):].lower() == suffix


def _parse_tone(line):
    text = line.strip()
    if not text or text[0] == "#":
        return 0, 0
    parts = text.split()
    if len(parts) < 2:
        return 0, 0
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return 0, 0
