import os
import glob
import shutil
import librosa
import subprocess as sp
import numpy as np
from .qpfile_chapter import GCFQP


encdict = {'.hevc': 'x265', '.264': 'x264', '.avc': 'x264'}
g_eac3to_fp = 'eac3to'
g_tsmuxer_fp = 'tsmuxer'
g_ffmpeg_fp = 'ffmpeg'
g_ffprobe_fp = 'ffprobe'
g_mkvmerge_fp = 'mkvmerge'


def load_audio(audio_fp):
    return librosa.load(audio_fp, sr=None, mono=False)[0]


def flac_with_eac3to(src_fn, dst_fn, shift):
    shift = 0 if shift is None else int(shift)
    flac_cmd = f'"{g_eac3to_fp}" "{src_fn}" "{dst_fn}"'
    if shift != 0:
        flac_cmd += f' {shift:+d}ms'
    _ = sp.run(flac_cmd)


def flac_with_ffmpeg(src_fp, dst_fp, shift):
    shift = 0 if shift is None else int(shift)
    flac_cmd = [g_ffmpeg_fp, '-i', src_fp, '-compression_level', 12]
    if shift > 0:
        flac_cmd += ['-af', f'adelay={shift}']
    elif shift < 0:
        flac_cmd += ['-ss', str(-shift/1000)]
    flac_cmd += ['-y', dst_fp]
    _ = sp.run(flac_cmd)


def demux_with_eac3to(fn, demux_fp, keeptrack):
    # get track info from eac3to logfile
    name, ext = os.path.splitext(fn)
    media = ''
    _ = sp.run(f'"{g_eac3to_fp}" "{fn}" -log=_eac3to_analyze.txt')
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
    os.remove('_eac3to_analyze.txt')

    # demux and convert to flac using eac3to
    eac3to_cmd = f'"{g_eac3to_fp}" "{fn}" '
    for tid, track in enumerate(media, 1):
        if track in ['v', 'c']:
            continue
        track_ext = ".flac" if track == "a" else ".sup"
        eac3to_cmd += f'{tid}: {tid}{track_ext} '
    eac3to_cmd += f'-destpath="{name}.demux/"'
    _ = sp.run(eac3to_cmd)
    
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
                
    # demux as origin formats
    if keeptrack:
        _ = sp.run(f'"{g_eac3to_fp}" "{fn}" -demux -destpath="{name}.demux/"')
        for tid, track in enumerate(media, 1):
            if track != 'v':
                continue
            for v_fp in glob.glob(os.path.join(glob.escape(demux_fp), name + f' - {tid} *')):
                os.remove(v_fp)
    
    return to_merge_aud, to_merge_sub


def demux_with_tsmuxer(tar_fp, demux_fp, converter):
    # get track info and write meta file
    meta_fp = '_demux.meta'
    meta = ["MUXOPT --no-pcr-on-video-pid --new-audio-pes --demux --vbr --vbv-len=500"]
    track_meta, fps, timeshift, tid, tidshift = None, None, None, [], []
    info_p = sp.Popen([g_tsmuxer_fp, tar_fp], stdout=sp.PIPE, stderr=sp.PIPE)
    info_r = info_p.communicate()
    for msg in info_r[0].decode().splitlines():
        if msg.startswith("Track ID:"):
            tid.append(msg[9:].strip())
        elif msg.startswith("Stream ID:"):
            code = msg[10:].strip()
            if code.startswith('V'):
                _ = tid.pop()
            elif code.startswith('A'):
                track_meta = R'{}, "{}", track={}'.format(code, tar_fp, tid[-1])
            else:  # startswith('S')
                track_meta = R'{}, "{}", fps={}, track={}'.format(code, tar_fp, fps, tid[-1])
        elif msg.startswith("Stream delay:"):
            timeshift = msg[13:].strip()
            if track_meta:
                track_meta += f', timeshift={timeshift}ms'
        elif fps is None and msg.startswith("Stream info:"):
            fps = msg.split('Frame rate:')[-1].strip().split(' ')[0]
        elif msg == '':  # end of a track block
            if track_meta:
                meta.append(track_meta)
                tidshift.append(timeshift)
                track_meta = None
                timeshift = None
    with open(meta_fp, 'wt') as metafile:
        _ = metafile.write(os.linesep.join(meta))
    
    # run demuxer
    _ = sp.run([g_tsmuxer_fp, meta_fp, demux_fp])
    os.remove(meta_fp)

    # convert to flac and check audio dupe
    to_merge_aud, to_merge_sub = [], []
    last_aud, this_aud = None, None
    demux_list = os.listdir(demux_fp)
    for id, shift in zip(tid, tidshift):
        track_fp = None
        for fn in demux_list:
            if f'track_{id}.' in fn:
                track_fp = os.path.join(demux_fp, fn)
                break
        if track_fp.endswith('.sup'):
            to_merge_sub.append(track_fp)
            continue
        flac_fp = os.path.splitext(track_fp)[0] + '.flac'
        if converter == 'eac3to':
            os.chdir(demux_fp)
            track_fn = os.path.basename(track_fp)
            flac_fn = os.path.basename(flac_fp)
            flac_with_eac3to(track_fn, flac_fn, shift)
            os.chdir(os.path.dirname(tar_fp))
        else:
            flac_with_ffmpeg(track_fp, flac_fp, shift)
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
    
    return to_merge_aud, to_merge_sub


def mux_mkv(mux_path, name, w, h, vc_ext, vc_fp, to_merge_aud, to_merge_sub, chap_fp):
    mkv_fp = os.path.join(mux_path, name + f' (BD {w}x{h} {encdict[vc_ext]}')
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
    mkvmerge_cmd = [g_mkvmerge_fp, '-o', mkv_fp, vc_fp]
    mkvmerge_cmd += ['--generate-chapters-name-template', '', '--chapters', chap_fp]
    for aud in to_merge_aud:
        mkvmerge_cmd.append(aud)
    for sub in to_merge_sub:
        mkvmerge_cmd.append(sub)
    _ = sp.run(mkvmerge_cmd)


def dfs(mux_path, keeptrack, vc_ext, demuxer, converter, recursion):
    mux_path = os.path.abspath(mux_path)
    for fn in os.listdir(mux_path):
        # dfs decision
        tar_fp = os.path.join(mux_path, fn)
        if os.path.isdir(tar_fp):
            if recursion:
                dfs(
                    mux_path=tar_fp,
                    recursion=recursion,
                    vc_ext=vc_ext,
                    keeptrack=keeptrack,
                    demuxer=demuxer,
                    converter=converter,
                )
            continue
        os.chdir(mux_path)
        
        # file decision
        name, ext = os.path.splitext(fn)
        vc_fp = os.path.join(mux_path, name + vc_ext)
        if ext not in ['.m2ts'] or not os.path.exists(vc_fp):
            continue
        if os.path.exists(vc_fp + '.break') or os.path.exists(vc_fp + '.busy'):
            continue
        if len(glob.glob(glob.escape(os.path.join(mux_path, name)) + '*.mkv')) > 0:
            continue
        
        # create demux folder
        demux_fp = os.path.join(mux_path, name + '.demux')
        if os.path.exists(demux_fp):
            if os.path.isdir(demux_fp):
                shutil.rmtree(demux_fp)
            else:
                os.remove(demux_fp)
        os.makedirs(demux_fp)
        
        # demux with selected demuxer
        if demuxer == 'eac3to':
            to_merge_aud, to_merge_sub = demux_with_eac3to(fn, demux_fp, keeptrack)
        else:
            to_merge_aud, to_merge_sub = demux_with_tsmuxer(tar_fp, demux_fp, converter)

        # generate pts chapter from qpfile
        qp_fp = os.path.join(mux_path, name + '.qpfile')
        chap_fp = os.path.join(mux_path, name + '.chapter.txt')
        w, h =  GCFQP(vc_fp, qp_fp, chap_fp, g_ffprobe_fp, g_mkvmerge_fp)

        # mux
        mux_mkv(mux_path, name, w, h, vc_ext, vc_fp, to_merge_aud, to_merge_sub, chap_fp)

        # recycle
        if not keeptrack:
            shutil.rmtree(demux_fp)


def mux_bd(
    mux_path: str,
    keeptrack: bool = False,  # whether to keep the demux audio & sub tracks
    vc_ext: str = '.hevc',
    recursion: bool = True, 
    eac3to_fp: str = None,
    tsmuxer_fp: str = None,
    ffmpeg_fp: str = None,
    ffprobe_fp: str = None,
    mkvmerge_fp: str = None,
):
    global g_eac3to_fp, g_tsmuxer_fp, g_ffmpeg_fp, g_ffprobe_fp, g_mkvmerge_fp
    path_record = os.path.abspath('.')
    g_eac3to_fp = shutil.which(eac3to_fp or g_eac3to_fp)
    g_tsmuxer_fp = shutil.which(tsmuxer_fp or g_tsmuxer_fp)
    g_ffmpeg_fp = shutil.which(ffmpeg_fp or g_ffmpeg_fp)
    g_ffprobe_fp = shutil.which(ffprobe_fp or g_ffprobe_fp)
    g_mkvmerge_fp = shutil.which(mkvmerge_fp or g_mkvmerge_fp)
    assert g_eac3to_fp or g_tsmuxer_fp, 'No demuxer survives.'
    assert g_eac3to_fp or g_ffmpeg_fp, 'No audio converter survives.'
    demuxer = 'tsmuxer' if g_tsmuxer_fp else 'eac3to'
    converter = 'eac3to' if g_eac3to_fp else 'ffmpeg'
    dfs(mux_path, keeptrack, vc_ext, demuxer, converter, recursion)
    g_eac3to_fp = 'eac3to'
    g_tsmuxer_fp = 'tsmuxer'
    g_ffmpeg_fp = 'ffmpeg'
    g_ffprobe_fp = 'ffprobe'
    g_mkvmerge_fp = 'mkvmerge'
    os.chdir(path_record)
    