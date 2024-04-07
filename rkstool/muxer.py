import os
import glob
import shutil
import librosa
import subprocess as sp
from .qpfile_chapter import GCFQP


encdict = {'.hevc': 'x265', '.264': 'x264', '.avc': 'x264'}
_ffprobe_fp = 'ffprobe'
_ffmpeg_fp = 'ffmpeg'
_tsmuxer_fp = 'tsmuxer'
_mkvmerge_fp = 'mkvmerge'


def load_audio(audio_fp):
    return librosa.load(audio_fp, sr=None, mono=False)[0]


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
        meta_fp = '_demux.meta'
        demux_fp = os.path.join(mux_path, '_tsmuxer_demux')
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
        meta = ["MUXOPT --no-pcr-on-video-pid --new-audio-pes --demux --vbr --vbv-len=500"]
        track_meta = None
        tid = []
        fps = None
        for msg in r[0].decode().splitlines():
            if msg.startswith("Track ID:"):
                tid.append(msg[9:].strip())
            elif msg.startswith("Stream ID:"):
                code = msg[10:].strip()
                if code.startswith('V'):
                    _ = tid.pop()
                elif code.startswith('A'):
                    track_meta = r'{}, "{}", track={}'.format(code, tar_fp, tid[-1])
                else:
                    track_meta = r'{}, "{}", fps={}, track={}'.format(code, tar_fp, fps, tid[-1])
            elif msg.startswith("Stream delay:"):
                timeshift = msg[13:].strip()
                if track_meta:
                    track_meta += f', timeshift={timeshift}ms'
            elif fps is None and msg.startswith("Stream info:"):
                fps = msg.split('Frame rate:')[-1].strip().split(' ')[0]
            elif msg == '':  # end of a track block
                if track_meta:
                    meta.append(track_meta)
                    track_meta = None
        with open(meta_fp, 'wt') as metafile:
            _ = metafile.write(os.linesep.join(meta))
        
        p = sp.Popen([_tsmuxer_fp, meta_fp, demux_fp])
        r = p.communicate()

        # check audio dupe
        to_merge_aud, to_merge_sub = [], []
        demux_list = os.listdir(demux_fp)
        for id in tid:
            track_fp = None
            for fn in demux_list:
                if f'track_{id}' in fn:
                    track_fp = os.path.join(demux_fp, fn)
                    break
            if track_fp.endswith('.sup'):
                to_merge_sub.append()
            

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
        r = p.communicate()

        os.remove(meta_fp)
        shutil.rmtree(demux_fp)


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
