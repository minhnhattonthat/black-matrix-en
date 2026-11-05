"""Clips for a human ear: each stretch of a movie's vocal track that machines can't settle, cut from the original mix and the vocal track, 0.5 s either side.
usage: fmv_listen.py    -> work/movies/listen/NAME_FIRST-LAST_{mix,voice}.wav (frames at 15 fps)"""
from pathlib import Path

from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
ASR = ROOT / 'work/movies/asr'
OUT = ROOT / 'work/movies/listen'
# Silero spans on the vocal track where whisper reads nothing, and the longest voiced stretches
SPANS = [('0102', 5, 37), ('0103', 3, 61), ('0201', 9, 65), ('0601', 33, 69), ('0902', 234, 247), ('1101', 34, 53), ('1102', 122, 136), ('1102', 292, 305),
         ('1204', 17, 30), ('1204', 185, 207), ('1205', 78, 117), ('1001', 100, 123), ('1201', 84, 281), ('1206', 1277, 1421), ('OPENING', 168, 225),
         ('PROLOGUE', 1093, 1180), ('DEMO01', 2709, 3000)]


def cut(path, lo, hi, out):
    rate, a = wavfile.read(path)
    wavfile.write(out, rate, a[max(0, int((lo / 15 - .5) * rate)):int((hi / 15 + .5) * rate)])


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for name, lo, hi in SPANS:
        cut(ASR / f'{name}.wav', lo, hi, OUT / f'{name}_{lo:04d}-{hi:04d}_mix.wav')
        cut(ASR / f'stem/{name}.wav', lo, hi, OUT / f'{name}_{lo:04d}-{hi:04d}_voice.wav')
    print(len(SPANS), 'stretches ->', OUT)
