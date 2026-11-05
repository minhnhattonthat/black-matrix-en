"""Speech in the movies: extract each movie's XA audio and transcribe it with faster-whisper.
usage: fmv_asr.py [NAME ..]   default every movie on both discs -> work/movies/asr/NAME.wav, NAME.json, NAME.vad.json (frame spans)
       fmv_asr.py --stems     the same on the vocal tracks from tools/fmv_vocals.py, for lines buried under music
A movie runs at 15 fps (10 sectors a frame at 2x), so frame = seconds * 15. VAD stays off: with it on, lines went missing (skill, platform-ps1.md)."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / 'tools/jpsxdec/jpsxdec_v2.0/jpsxdec.jar'
OUT = ROOT / 'work/movies/asr'


def movies():
    found = {}
    for disc in (1, 2):
        for p in sorted((ROOT / f'work/orig/d{disc}/MOVIE').glob('*.STR')):
            found.setdefault(p.stem, p)
    return found


def audio(name, src):
    """NAME.wav from the movie's first XA stream; None when it has none."""
    wav = OUT / f'{name}.wav'
    if wav.exists():
        return wav
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    idx = d / 'x.idx'
    subprocess.run(['java', '-jar', str(JAR), '-f', str(src), '-x', str(idx)], check=True, stdout=subprocess.DEVNULL, cwd=d)  # jPSXdec drops logs in its cwd
    items = re.findall(r'^#:(\d+)\|.*Type:XA', idx.read_text(encoding='utf-8'), re.M)
    if not items:
        return None
    subprocess.run(['java', '-jar', str(JAR), '-x', str(idx), '-i', items[0], '-dir', str(d), '-audf', 'wav'], check=True, stdout=subprocess.DEVNULL, cwd=d)
    next(d.rglob('*.wav')).replace(wav)
    return wav


def samples(wav):
    """Mono 16 kHz floats; faster-whisper's own decoder needs a PyAV this machine doesn't have."""
    rate, a = wavfile.read(wav)
    return signal.resample_poly(a.reshape(len(a), -1).mean(axis=1) / 32768, 16000, rate).astype(np.float32)  # some movies are mono


def stems():
    """Whisper and Silero on each Demucs vocal track, and on each Silero span cut out alone: work/movies/asr/stem/NAME.json (tools/fmv_vocals.py)."""
    from faster_whisper import WhisperModel
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    model = WhisperModel('large-v3', device='cpu', compute_type='int8', cpu_threads=8)
    d = OUT / 'stem'
    say = lambda pcm: [(round(s.start * 15), round(s.end * 15), round(s.no_speech_prob, 2), round(s.avg_logprob, 2), s.text.strip()) for s in
                       model.transcribe(pcm, language='ja', vad_filter=False, beam_size=5, condition_on_previous_text=False)[0]]
    for wav in sorted(d.glob('*.wav')):
        out = d / f'{wav.stem}.json'
        if out.exists():
            continue
        pcm = samples(wav)
        spans = [(s['start'], s['end']) for s in get_speech_timestamps(pcm, VadOptions(threshold=.3))]
        out.write_text(json.dumps({
            'peak': round(float(np.abs(pcm).max()), 4),
            'whole': say(pcm),
            'spans': [{'frames': (round(a / 16000 * 15), round(b / 16000 * 15)), 'rms': round(float(np.sqrt((pcm[a:b] ** 2).mean())), 4),
                       'said': say(np.concatenate([np.zeros(8000, np.float32), pcm[a:b], np.zeros(8000, np.float32)]))} for a, b in spans],
        }, ensure_ascii=False), encoding='utf-8')
        print(wav.stem, len(spans), 'spans', flush=True)


def main(names):
    if names == ['--stems']:
        return stems()
    from faster_whisper import WhisperModel
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    OUT.mkdir(parents=True, exist_ok=True)
    found = movies()
    model = WhisperModel('large-v3', device='cpu', compute_type='int8')  # no CUDA libraries here; about 25 min of audio in all
    for name in names or found:
        if not names and (OUT / f'{name}.json').exists():
            continue
        wav = audio(name, found[name])
        if wav is None:
            print(name, 'no audio', flush=True)
            continue
        pcm = samples(wav)
        # no initial_prompt: on a silent stretch whisper reads it back as speech. Silero's spans are a second opinion on silence-filler lines
        spans = get_speech_timestamps(pcm, VadOptions(threshold=.3))
        (OUT / f'{name}.vad.json').write_text(json.dumps([(round(s['start'] / 16000 * 15), round(s['end'] / 16000 * 15)) for s in spans]))
        segs, _ = model.transcribe(pcm, language='ja', vad_filter=False, beam_size=5, word_timestamps=True, condition_on_previous_text=False)
        rows =[{'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip(), 'logprob': round(s.avg_logprob, 2),
                 'no_speech': round(s.no_speech_prob, 2),
                 'words': [(round(w.start, 2), round(w.end, 2), w.word) for w in s.words]} for s in segs]
        (OUT / f'{name}.json').write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding='utf-8')
        print(name, len(rows), 'segments', flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
