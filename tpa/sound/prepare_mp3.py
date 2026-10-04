#!/usr/bin/env python3
"""Turn an MP3 into frequencies the EV3 speaker can play.

Run this on a computer, then copy the ``.tones`` file to the brick.
``RobotSound.play()`` reads each ``frequency_hz duration_ms`` line and calls
``speaker.beep()``. Silence is written as 0 Hz: the brick plays any frequency
below 100 Hz as 100 Hz, so a rest must not be sent to ``beep()``.
"""

import os
import struct
import subprocess
import sys

SAMPLE_RATE = 8000
FRAME_MS = 40
MIN_HZ = 100
MAX_HZ = 2500
SILENCE_RATIO = 0.12
MERGE_TOLERANCE = 0.08
CLARITY = 0.8


def decode_mp3(path, sample_rate):
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        path,
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "pipe:1",
    ]
    try:
        raw = subprocess.check_output(command, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise SystemExit("ffmpeg is required to decode mp3")
    except subprocess.CalledProcessError as error:
        message = error.stderr.decode("utf-8", "replace").strip()
        raise SystemExit("ffmpeg failed: " + message)
    count = len(raw) // 2
    if count == 0:
        return []
    return list(struct.unpack("<{0}h".format(count), raw[: count * 2]))


def estimate_pitch(samples, sample_rate, min_hz=MIN_HZ, max_hz=MAX_HZ):
    count = len(samples)
    if count < 4:
        return 0

    mean = 0.0
    for sample in samples:
        mean += sample
    mean /= float(count)
    centered = [sample - mean for sample in samples]

    min_lag = int(round(sample_rate / float(max_hz)))
    if min_lag < 1:
        min_lag = 1
    max_lag = int(round(sample_rate / float(min_hz))) + 1
    if max_lag > count // 2 - 1:
        max_lag = count // 2 - 1
    if max_lag <= min_lag:
        return 0

    correlation = [0.0] * (max_lag + 1)
    for lag in range(1, max_lag + 1):
        product = 0.0
        left_energy = 0.0
        right_energy = 0.0
        for index in range(count - lag):
            left = centered[index]
            right = centered[index + lag]
            product += left * right
            left_energy += left * left
            right_energy += right * right
        denominator = left_energy + right_energy
        if denominator > 0.0:
            correlation[lag] = 2.0 * product / denominator

    peaks = []
    for lag in range(min_lag, max_lag):
        value = correlation[lag]
        if value > 0.3 and value >= correlation[lag - 1] and value >= correlation[lag + 1]:
            peaks.append(lag)
    if not peaks:
        return 0

    best = correlation[peaks[0]]
    for lag in peaks:
        if correlation[lag] > best:
            best = correlation[lag]
    if best < 0.5:
        return 0

    chosen = 0
    for lag in peaks:
        if correlation[lag] >= CLARITY * best:
            chosen = lag
            break
    if chosen == 0:
        return 0

    previous = correlation[chosen - 1]
    current = correlation[chosen]
    following = correlation[chosen + 1]
    denominator = previous - 2.0 * current + following
    shift = 0.0
    if denominator != 0.0:
        shift = 0.5 * (previous - following) / denominator
        if not -1.0 < shift < 1.0:
            shift = 0.0
    return int(round(sample_rate / float(chosen + shift)))


def _rms(samples):
    total = 0.0
    for sample in samples:
        total += sample * sample
    return (total / float(len(samples))) ** 0.5


def frames_to_notes(samples, sample_rate, frame_ms):
    frame_size = int(sample_rate * frame_ms / 1000)
    if frame_size < 2 or len(samples) < frame_size:
        return []

    measured = []
    for start in range(0, len(samples) - frame_size + 1, frame_size):
        frame = samples[start : start + frame_size]
        measured.append((_rms(frame), estimate_pitch(frame, sample_rate)))

    peak = 0.0
    for rms, _pitch in measured:
        if rms > peak:
            peak = rms
    gate = peak * SILENCE_RATIO

    notes = []
    for rms, pitch in measured:
        if rms < gate or pitch < MIN_HZ:
            notes.append((0, frame_ms))
        else:
            if pitch > 10000:
                pitch = 10000
            notes.append((pitch, frame_ms))
    return _merge(notes)


def _merge(notes):
    if not notes:
        return []
    merged = [notes[0]]
    for frequency, duration in notes[1:]:
        previous_frequency, previous_duration = merged[-1]
        same_silence = frequency == 0 and previous_frequency == 0
        close_pitch = False
        if frequency > 0 and previous_frequency > 0:
            spread = abs(frequency - previous_frequency) / float(previous_frequency)
            close_pitch = spread <= MERGE_TOLERANCE
        if same_silence or close_pitch:
            merged[-1] = (previous_frequency, previous_duration + duration)
        else:
            merged.append((frequency, duration))
    return merged


def write_tones(path, notes):
    handle = open(path, "w")
    try:
        handle.write("# frequency_hz duration_ms\n")
        handle.write("# 0 Hz is silence: beep() would play it as 100 Hz\n")
        for frequency, duration in notes:
            handle.write("{0} {1}\n".format(frequency, duration))
    finally:
        handle.close()


def prepare(mp3_path, output_path=None):
    if output_path is None:
        output_path = os.path.splitext(mp3_path)[0] + ".tones"
    samples = decode_mp3(mp3_path, SAMPLE_RATE)
    notes = frames_to_notes(samples, SAMPLE_RATE, FRAME_MS)
    write_tones(output_path, notes)
    return output_path, len(notes)


def _mp3_files(directory):
    names = []
    for name in os.listdir(directory):
        if name.lower().endswith(".mp3"):
            names.append(os.path.join(directory, name))
    names.sort()
    return names


def main(argv):
    if len(argv) < 2:
        raise SystemExit(
            "usage: python3 prepare_mp3.py <file.mp3 | directory> [output.tones]"
        )
    source = argv[1]
    if os.path.isdir(source):
        files = _mp3_files(source)
        if not files:
            raise SystemExit("no mp3 in " + source)
        for mp3_path in files:
            output_path, count = prepare(mp3_path)
            print("{0} -> {1} ({2} notes)".format(mp3_path, output_path, count))
        return
    output_path = argv[2] if len(argv) > 2 else None
    written, count = prepare(source, output_path)
    print("{0} -> {1} ({2} notes)".format(source, written, count))


if __name__ == "__main__":
    main(sys.argv)
