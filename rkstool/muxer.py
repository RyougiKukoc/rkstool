import os
import glob
import librosa
import subprocess as sp
from .qpfile_chapter import GCFQP


encdict = {'.hevc': 'x265', '.264': 'x264', '.avc': 'x264'}
_eac3to_fp = 'eac3to'
_ffprobe_fp = 'ffprobe'
_tsmuxer_fp = 'tsmuxer'
_mkvmerge_fp = 'mkvmerge'


def load_audio(audio_fp):
    return librosa.load(audio_fp, sr=librosa.get_samplerate(audio_fp), mono=False)[0]


def dfs(
    mux_path: str,
    recursion: bool = True, 
    vc_ext: str = '.hevc',
):
    enc = encdict[vc_ext]
    mux_path = os.path.abspath(mux_path)
    for fn in os.listdir(mux_path):
        tar_fp = os.path.join(mux_path, fn)
        if os.path.isdir(tar_fp):
            if recursion:
                dfs(
                    mux_path=tar_fp,
                    recursion=recursion,
                    vc_ext=vc_ext,
                )
            continue
        os.chdir(mux_path)  # len(path) problem in eac3to
        name, ext = os.path.splitext(fn)
        vc_fp = os.path.join(mux_path, name + vc_ext)
        qp_fp = os.path.join(mux_path, name + '.qpfile')
        chap_fp = os.path.join(mux_path, name + '.chapter.txt')
        busy_fp = vc_fp + '.busy'
        break_fp = vc_fp + '.break'
        if ext not in ['.m2ts']:
            continue
        if not os.path.exists(vc_fp):
            continue
        if os.path.exists(break_fp):
            continue
        if os.path.exists(busy_fp):
            continue
        if len(glob.glob(os.path.join(glob.escape(mux_path), name + '*.mkv'))) > 0:
            continue
        
        # use tsmuxer to fetch stream info
        p = sp.Popen([_tsmuxer_fp, tar_fp], stdout=sp.PIPE, stderr=sp.PIPE)
        r = p.communicate()
        flag = False  # flag: a start of a period of track
        media = ""
        for msg in r[0].decode().split('\r\n'):
            if flag is False:
                if msg.startswith("Track ID:"):
                    flag = True
            else:
                if msg.startswith("Stream ID:"):
                    code = msg[10:].strip()
                    if code.startswith('V'):
                        media += 'v'
                    elif code.startswith('A'):
                        media += 'a'
                    else:
                        media += 's'
                    flag = False
        
        # use eac3to to 
        to_merge_sub = []
        to_merge_aud = []
        eac3to_cmd = [_eac3to_fp, fn]
        for id, track in enumerate(media, 1):
            if track == 'a':
                # aud_fp = os.path.join(mux_path, f'_mux_{id}a.flac')
                eac3to_cmd += [f'{id}:', f'_mux_{id}a.flac']
            elif track == 's':
                # sub_fp = os.path.join(mux_path, f'_mux_{id}s.sup')
                eac3to_cmd += [f'{id}:', f'_mux_{id}s.sup']
                to_merge_sub += [f'_mux_{id}s.sup']
        eac3to_cmd += ['-log=NUL']
        p = sp.Popen(eac3to_cmd)
        r = p.communicate()

        # check audio dupe
        for id, track in enumerate(media, 1):
            if track == 'a':
                # aud_fp = os.path.join(mux_path, f'_mux_{id}a.flac')
                aud_fp = f'_mux_{id}a.flac'
                if len(to_merge_aud) == 0:
                    to_merge_aud += [aud_fp]
                    last_aud = load_audio(aud_fp)
                    continue
                this_aud = load_audio(aud_fp)
                if last_aud.shape == this_aud.shape:
                    if ((last_aud - this_aud) ** 2).mean() < 1e-8:
                        continue
                to_merge_aud += [aud_fp]
                last_aud = this_aud

        # generate pts chapter from qpfile
        w, h =  GCFQP(vc_fp, qp_fp, chap_fp, _ffprobe_fp, _mkvmerge_fp)

        mkv_fp = os.path.join(mux_path, name + f' (BD {w}x{h} {enc}')
        num_a = len(to_merge_aud)
        num_s = len(to_merge_sub)
        if num_a > 1:
            mkv_fp += f' FLACx{num_a}'
        elif num_a == 1:
            mkv_fp += f' FLAC'
        if num_s > 1:
            mkv_fp += f' SUPx{num_s}'
        elif num_s == 1:
            mkv_fp += f' SUP'
        mkv_fp += ').mkv'
        mkvmerge_cmd = [_mkvmerge_fp, '-o', mkv_fp, vc_fp]
        mkvmerge_cmd += ['--generate-chapters-name-template', '', '--chapters', chap_fp]
        for aud in to_merge_aud:
            mkvmerge_cmd += [aud]
        for sub in to_merge_sub:
            mkvmerge_cmd += [sub]
        p = sp.Popen(mkvmerge_cmd)
        r = p.communicate()

        for id, track in enumerate(media, 1):
            if track == 'a':
                # aud_fp = os.path.join(mux_path, f'_mux_{id}a.flac')
                os.remove(f'_mux_{id}a.flac')
            elif track == 's':
                # sub_fp = os.path.join(mux_path, f'_mux_{id}s.sup')
                os.remove(f'_mux_{id}s.sup')


def mux_bd(
    mux_path: str,
    recursion: bool = True, 
    vc_ext: str = '.hevc',
    eac3to_fp: str = None,
    ffprobe_fp: str = None,
    tsmuxer_fp: str = None,
    mkvmerge_fp: str = None,
):
    if eac3to_fp is not None:
        global _eac3to_fp
        _eac3to_fp = eac3to_fp
    if ffprobe_fp is not None:
        global _ffprobe_fp
        _ffprobe_fp = ffprobe_fp
    if tsmuxer_fp is not None:
        global _tsmuxer_fp
        _tsmuxer_fp = tsmuxer_fp
    if mkvmerge_fp is not None:
        global _mkvmerge_fp
        _mkvmerge_fp = mkvmerge_fp
    dfs(mux_path, recursion, vc_ext)
