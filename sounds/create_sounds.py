import math
import wave
import struct
import os


SAMPLE_RATE = 44100


def create_tone(filename, frequency, duration, volume=0.3):
    os.makedirs("sounds", exist_ok=True)

    samples = int(SAMPLE_RATE * duration)

    with wave.open(filename, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)

        for i in range(samples):
            t = i / SAMPLE_RATE

            # Fade in and fade out to avoid clicks
            fade = min(
                1.0,
                i / (SAMPLE_RATE * 0.01),
                (samples - i) / (SAMPLE_RATE * 0.03)
            )

            value = (
                math.sin(2 * math.pi * frequency * t)
                * volume
                * fade
            )

            wav.writeframes(
                struct.pack("<h", int(value * 32767))
            )


create_tone("sounds/bounce.wav", 500, 0.08, 0.25)
create_tone("sounds/goal.wav", 800, 0.30, 0.30)
create_tone("sounds/timeout.wav", 220, 0.50, 0.30)

print("Sound files created successfully.")