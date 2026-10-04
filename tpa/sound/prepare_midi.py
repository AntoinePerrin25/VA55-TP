#!/usr/bin/env python3
"""Turn a MIDI file into one melody line the EV3 speaker can play.

The brick plays a single frequency with speaker.beep(). A piano MIDI sounds
many notes at once, so this keeps only the tune: the highest note still in
the melody register. Left-hand notes are written as silence.

    python3 sound/prepare_midi.py sound/circus.mid
"""

import os
import struct
import sys

MELODY_FLOOR = 60
MAX_DROP = 18
MIN_REST_MS = 40
MAX_NOTE_MS = 500


def _varlen(data, pos):
    value = 0
    while True:
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos


def _parse(data):
    if data[:4] != b"MThd":
        raise SystemExit("not a midi file")
    header_len = struct.unpack(">I", data[4:8])[0]
    _fmt, track_count, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        raise SystemExit("smpte midi timing is not supported")
    pos = 8 + header_len
    notes = []
    tempos = [(0, 500000)]
    for _track in range(track_count):
        if data[pos : pos + 4] != b"MTrk":
            raise SystemExit("missing midi track")
        pos += 4
        track_len = struct.unpack(">I", data[pos : pos + 4])[0]
        pos += 4
        end = pos + track_len
        tick = 0
        running = None
        pending = {}
        while pos < end:
            delta, pos = _varlen(data, pos)
            tick += delta
            status = data[pos]
            if status < 0x80:
                status = running
            else:
                pos += 1
                running = status
            kind = status & 0xF0
            if kind in (0x80, 0x90):
                pitch = data[pos]
                velocity = data[pos + 1]
                pos += 2
                if kind == 0x80 or velocity == 0:
                    started = pending.get(pitch)
                    if started:
                        notes.append((started.pop(0), tick, pitch))
                else:
                    pending.setdefault(pitch, []).append(tick)
            elif kind in (0xA0, 0xB0, 0xE0):
                pos += 2
            elif kind in (0xC0, 0xD0):
                pos += 1
            elif status == 0xFF:
                running = None
                meta = data[pos]
                pos += 1
                length, pos = _varlen(data, pos)
                payload = data[pos : pos + length]
                pos += length
                if meta == 0x51 and length == 3:
                    tempo = (payload[0] << 16) | (payload[1] << 8) | payload[2]
                    tempos.append((tick, tempo))
                if meta == 0x2F:
                    break
            elif status in (0xF0, 0xF7):
                length, pos = _varlen(data, pos)
                pos += length
            else:
                raise SystemExit("bad midi event")
        for pitch, starts in pending.items():
            for start in starts:
                notes.append((start, tick, pitch))
    tempos.sort()
    return notes, tempos, division


def _ms(tick, tempos, division):
    microseconds = 0
    for index, (start, tempo) in enumerate(tempos):
        if tick <= start:
            break
        next_tick = tempos[index + 1][0] if index + 1 < len(tempos) else tick
        span = min(tick, next_tick) - start
        microseconds += span * tempo / float(division)
    return int(round(microseconds / 1000.0))


def _melody(notes):
    events = {}
    for start, end, pitch in notes:
        events.setdefault(start, []).append((0, pitch))
        events.setdefault(end, []).append((1, pitch))
    sounding = {}
    melody = []
    last_tick = 0
    last_pitch = 0
    recent = None
    for tick in sorted(events):
        for kind, pitch in sorted(events[tick]):
            if kind == 1:
                count = sounding.get(pitch, 0) - 1
                if count <= 0:
                    sounding.pop(pitch, None)
                else:
                    sounding[pitch] = count
            else:
                sounding[pitch] = sounding.get(pitch, 0) + 1
        candidates = [pitch for pitch in sounding if pitch >= MELODY_FLOOR]
        if recent is not None:
            candidates = [pitch for pitch in candidates if pitch >= recent - MAX_DROP]
        chosen = max(candidates) if candidates else 0
        if chosen != last_pitch and tick > last_tick:
            melody.append((last_tick, tick, last_pitch))
            last_tick = tick
            last_pitch = chosen
        elif chosen != last_pitch:
            last_tick = tick
            last_pitch = chosen
        if chosen:
            recent = chosen
    if notes:
        end_tick = max(end for _start, end, _pitch in notes)
        if end_tick > last_tick:
            melody.append((last_tick, end_tick, last_pitch))
    return melody


def _hz(note):
    return int(round(440.0 * (2.0 ** ((note - 69) / 12.0))))


def _moving_notes(notes, tempos, division):
    moving = []
    for start, end, pitch in notes:
        duration = _ms(end, tempos, division) - _ms(start, tempos, division)
        if 0 < duration <= MAX_NOTE_MS:
            moving.append((start, end, pitch))
    return moving


def to_tones(notes, tempos, division):
    tones = []
    for start, end, pitch in _melody(_moving_notes(notes, tempos, division)):
        duration = _ms(end, tempos, division) - _ms(start, tempos, division)
        if duration <= 0:
            continue
        frequency = 0 if pitch < MELODY_FLOOR else _hz(pitch)
        if frequency and frequency < 100:
            frequency = 100
        if tones and frequency == tones[-1][0]:
            tones[-1] = (frequency, tones[-1][1] + duration)
        elif frequency == 0 and duration < MIN_REST_MS and tones:
            tones[-1] = (tones[-1][0], tones[-1][1] + duration)
        else:
            tones.append((frequency, duration))
    return tones


def write_tones(path, tones):
    handle = open(path, "w")
    try:
        handle.write("# frequency_hz duration_ms\n")
        handle.write("# melody only; 0 Hz is silence\n")
        for frequency, duration in tones:
            handle.write("{0} {1}\n".format(frequency, duration))
    finally:
        handle.close()


def prepare(midi_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(midi_path)[0] + ".tones"
    data = open(midi_path, "rb").read()
    notes, tempos, division = _parse(data)
    tones = to_tones(notes, tempos, division)
    write_tones(output_path, tones)
    return output_path, len(tones)


def main(argv):
    if len(argv) < 2:
        raise SystemExit("usage: python3 prepare_midi.py <file.mid> [output.tones]")
    output_path = argv[2] if len(argv) > 2 else None
    written, count = prepare(argv[1], output_path)
    print("{0} -> {1} ({2} notes)".format(argv[1], written, count))


if __name__ == "__main__":
    main(sys.argv)
