import os
import glob
import shutil
import librosa
import subprocess as sp
import numpy as np
from .qpfile_chapter import GCFQP


encdict = {'.hevc': 'x265', '.264': 'x264', '.avc': 'x264'}
_ffprobe_fp = 'ffprobe'
_eac3to_fp = 'eac3to'
_mkvmerge_fp = 'mkvmerge'


def load_audio(audio_fp):
    return librosa.load(audio_fp, sr=None, mono=False)[0]


def dfs(
    mux_path: str,
    recursion: bool = True, 
    vc_ext: str = '.hevc',
    keeptrack: bool = False,
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
        os.chdir(mux_path)
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
        
        demux_fp = os.path.join(mux_path, name + '.demux')
        if os.path.exists(demux_fp):
            if os.path.isdir(demux_fp):
                shutil.rmtree(demux_fp)
            else:
                os.remove(demux_fp)
        os.makedirs(demux_fp)
        
        media = ''
        p = sp.Popen([_eac3to_fp, tar_fp, '-log=', '_eac3to_analyze.txt'])
        _ = p.communicate()
        with open('_eac3to_analyze.txt', 'rt') as analyzefile:
            msgs = analyzefile.readlines()
        tid = 1
        for msg in msgs:
            if not msg.startswith(str(tid) + ':'):
                continue
            if 'ubtitle' in msg:  # must be subtitle
                media += 's'
            elif 'hannel' in msg:  # must be audio
                media += 'a'
            elif 'hapter' in msg:  # must be chapter
                media += 'c'
            else:
                media += 'v'
            tid += 1

        # demux and transcode to flac using eac3to
        eac3to_cmd = [_eac3to_fp, fn]
        for tid, track in enumerate(media, 1):
            if track in ['v', 'c']:
                continue
            track_ext = ".flac" if track == "a" else ".sup"
            eac3to_cmd += [f'{tid}:', str(tid) + track_ext]
        eac3to_cmd += ['-destpath=', f'{name}.demux/']
        p = sp.Popen(eac3to_cmd)
        _ = p.communicate()
        
        # check audio dupe
        last_aud, this_aud = None, None
        to_merge_aud, to_merge_sub = [], []
        for tid, track in enumerate(media, 1):
            if track == 's':
                to_merge_sub.append(os.path.join(demux_fp, f'{tid}.sup'))
            elif track == 'a':
                flac_fp = os.path.join(demux_fp, f'{tid}.flac')
                if len(to_merge_aud) == 0:
                    to_merge_aud.append(flac_fp)
                    last_aud = load_audio(flac_fp)
                else:
                    this_aud = load_audio(flac_fp)
                    if last_aud.shape == this_aud.shape:
                        if np.allclose(last_aud, this_aud):
                            with open(flac_fp + '.dupe', 'wt') as dupefile:
                                _ = dupefile.write('This file is the same as last track.')
                            continue
                    to_merge_aud.append(flac_fp)
                    last_aud = this_aud

        # generate pts chapter from qpfile
        w, h =  GCFQP(vc_fp, qp_fp, chap_fp, _ffprobe_fp, _mkvmerge_fp)

        mkv_fp = os.path.join(mux_path, name + f' (BD {w}x{h} {enc}')
        num_a = len(to_merge_aud)
        num_s = len(to_merge_sub)
        if num_a > 1:
            mkv_fp += f' FLACx{num_a}'
        elif num_a == 1:
            mkv_fp += ' FLAC'
        if num_s > 1:
            mkv_fp += f' SUPx{num_s}'
        elif num_s == 1:
            mkv_fp += ' SUP'
        mkv_fp += ').mkv'
        mkvmerge_cmd = [_mkvmerge_fp, '-o', mkv_fp, vc_fp]
        mkvmerge_cmd += ['--generate-chapters-name-template', '', '--chapters', chap_fp]
        for aud in to_merge_aud:
            mkvmerge_cmd += [aud]
        for sub in to_merge_sub:
            mkvmerge_cmd += [sub]
        p = sp.Popen(mkvmerge_cmd)
        _ = p.communicate()

        if keeptrack:
            p = sp.Popen([_eac3to_fp, fn, '-destpath=', f'{name}.demux/', '-log=NUL', '-demux'])
            _ = p.communicate()
            for tid, track in enumerate(media, 1):
                if track == 'v':
                    for v_fp in glob.glob(os.path.join(glob.escape(demux_fp), name + f' - {tid}*')):
                        os.remove(v_fp)
        else:
            shutil.rmtree(demux_fp)


def mux_bd(
    mux_path: str,
    recursion: bool = True, 
    vc_ext: str = '.hevc',
    keeptrack: bool = False,  # whether to keep the demux audio & sub tracks
    eac3to_fp: str = None,
    ffprobe_fp: str = None,
    mkvmerge_fp: str = None,
):
    if eac3to_fp is not None:
        global _eac3to_fp
        _eac3to_fp = eac3to_fp
    if ffprobe_fp is not None:
        global _ffprobe_fp
        _ffprobe_fp = ffprobe_fp
    if mkvmerge_fp is not None:
        global _mkvmerge_fp
        _mkvmerge_fp = mkvmerge_fp
    dfs(mux_path, recursion, vc_ext, keeptrack)
