"""Voices buried under a movie's music: split work/movies/asr/NAME.wav with Demucs into work/movies/asr/stem/NAME.wav (vocals only).
Also builds controls: known lines from 0101 mixed into music-only movies at set levels, split the same way, to measure what would be found.
Needs Demucs, kept out of the system Python: python -m venv V; V/Scripts/python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu; V/Scripts/python -m pip install demucs soundfile
usage: V/Scripts/python tools/fmv_vocals.py        then python tools/fmv_asr.py --stems"""
from pathlib import Path

import numpy as np
import soundfile
import torch
import torchaudio.functional as F
from demucs.apply import apply_model
from demucs.pretrained import get_model

ROOT = Path(__file__).resolve().parents[1]
ASR = ROOT / 'work/movies/asr'
STEM = ASR / 'stem'
# (first frame, last frame) of lines in 0101, at 15 fps
LINES = [(788, 903), (1013, 1127), (2192, 2287), (755, 764), (1845, 1858), (1279, 1301)]  # three sentences, three short words
BEDS = ['0701', '1206', 'STAFF']  # no speech found; loud music
LEVELS = [0, -6, -12, -18, -24]  # voice against the music's level, dB


def split(model, x, rate):
    """Vocals of float x (samples, channels)."""
    wav = torch.from_numpy(x.T).float()
    wav = F.resample(wav, rate, model.samplerate)
    ref = wav.mean(0)
    scale = ref.std() + 1e-8
    out = apply_model(model, ((wav - ref.mean()) / scale)[None], device='cpu', progress=False, overlap=.25)[0]
    vocals = out[model.sources.index('vocals')] * scale + ref.mean()
    return vocals.mean(0).numpy(), model.samplerate


def stereo(path):
    x, rate = soundfile.read(path, dtype='float32', always_2d=True)
    return (np.repeat(x, 2, axis=1) if x.shape[1] == 1 else x), rate


def rms(x):
    return float(np.sqrt((x * x).mean()))


def main():
    torch.set_num_threads(8)
    STEM.mkdir(parents=True, exist_ok=True)
    model = get_model('htdemucs')
    model.eval()
    for wav in sorted(ASR.glob('*.wav')):
        out = STEM / wav.name
        if not out.exists():
            soundfile.write(out, *split(model, *stereo(wav)), subtype='PCM_16')
            print(wav.stem, flush=True)

    # controls: a clean voice from 0101's stem, in the music of a movie with none
    voice, vrate = soundfile.read(STEM / '0101.wav', dtype='float32')
    for bed in BEDS:
        music, rate = stereo(ASR / f'{bed}.wav')
        for k, (lo, hi) in enumerate(LINES):
            line = voice[int(lo / 15 * vrate):int(hi / 15 * vrate)]
            line = F.resample(torch.from_numpy(line), vrate, rate).numpy()
            at = len(music) * (k % 3 + 1) // 4  # past the fade-in, inside any length of movie
            part = music[at:at + len(line)].mean(axis=1)
            for db in LEVELS:
                clip = music[max(0, at - 3 * rate):at + len(line) + 3 * rate].copy()
                gain = rms(part) / rms(line) * 10 ** (db / 20)
                clip[3 * rate:3 * rate + len(line)] += (line * gain)[:, None]
                name = f'ctl_{bed}_{k}_{db}'
                if (STEM / f'{name}.wav').exists():
                    continue
                soundfile.write(STEM / f'{name}.wav', *split(model, clip, rate), subtype='PCM_16')
                print(name, 'music rms', round(rms(part), 4), flush=True)


if __name__ == '__main__':
    main()
