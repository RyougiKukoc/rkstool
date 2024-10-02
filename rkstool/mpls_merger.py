import glob
import shutil
import os
import subprocess as sp
from .mpls_chapter import parse_mpls
from .logger import get_logger


g_ffmpeg_fp = 'ffmpeg'
g_mkvmerge_fp = 'mkvmerge'


def mmg(mpls_fp, mkv_dir, output_dir, logger):
    m2ts_list, mkv_list = [], []
    parse_mpls(mpls_fp, {}, m2ts_list)
    item_count = len(m2ts_list)
    for m2ts_fn in m2ts_list:
        mkv_matched = glob.glob(os.path.join(glob.escape(mkv_dir), f'*{m2ts_fn}*.mkv'))
        if len(mkv_matched) > 1:
            logger.warning(f'Multiple matching results for "*{m2ts_fn}*.mkv":')
            for mkv_fp in mkv_matched:
                logger.warning('->' + mkv_fp)
            logger.warning('Only the first one is picked.')
        elif len(mkv_matched) < 1:
            logger.info(f'No matching result for "*{m2ts_fn}*.mkv", {mpls_fp} is ignored.')
            return
        mkv_list.append(mkv_matched[0])
    
    output_fn = 'mpls' + os.path.basename(mpls_fp)[:-5]
    mkv_fn = os.path.basename(mkv_list[0])[:-4]
    if mkv_fn.endswith(')'):
        output_fn += ' (' + mkv_fn.split(')')[-2].split('(')[-1] + ')'
    output_fn += '.mkv'
    output_fp = os.path.join(output_dir, output_fn)

    if item_count == 1:
        shutil.copy2(mkv_list[0], output_fp)
        return

    audio_count = 0
    for i, mkv_fp in enumerate(mkv_list):
        p = sp.Popen([g_mkvmerge_fp, '-i', mkv_fp], stdout=sp.PIPE, stderr=sp.PIPE)
        mkvinfo = p.communicate()[0].decode()
        this_audio_count = 0
        for line in mkvinfo.splitlines():
            if 'audio' in line:
                if '(FLAC)' not in line:
                    logger.warning(f'{mkv_fp} {line} is not a FLAC audio track, {mpls_fp} is ignored.')
                    return
                else:
                    this_audio_count += 1
        if i == 0:
            audio_count = this_audio_count
        else:
            if audio_count != this_audio_count:
                logger.warning(
                    f'{mkv_fp} has {this_audio_count} audio tracks, ',
                    f'which is inequal to {mkv_list[0]} (who has {audio_count} audio tracks), ',
                    f'so {mpls_fp} is ignored.'
                )
                return
    
    concat_cmd = [g_ffmpeg_fp]
    for mkv_fp in mkv_list:
        concat_cmd += ['-i', mkv_fp]
    concat_cmd.append('-filter_complex')
    for i in range(audio_count):
        merged_flac_fp = os.path.join(output_dir, f'_a{i}.flac')
        tcmd = [''.join(f'[{j}:a:{i}]' for j in range(item_count)) + f'concat=n={item_count}:v=0:a=1[oa]']
        tcmd += ['-map', '[oa]', '-compression_level', '12', merged_flac_fp]
        _ = sp.run(concat_cmd + tcmd)
    
    append_cmd = [g_mkvmerge_fp, '-o', output_fp]
    for i, mkv_fp in enumerate(mkv_list):
        if i > 0:
            append_cmd += ['+']
        append_cmd += ['-A', mkv_fp]
    for i in range(audio_count):
        append_cmd += [os.path.join(output_dir, f'_a{i}.flac')]
    _ = sp.run(append_cmd)

    for i in range(audio_count):
        os.remove(os.path.join(output_dir, f'_a{i}.flac'))
            

def merge_mpls(
    mkv_dir: str,
    mpls_dir: str,
    output_dir: str,
    logger_fp: str = None,
    ffmpeg_fp = None,
    mkvmerge_fp = None,
):
    global g_ffmpeg_fp, g_mkvmerge_fp
    g_ffmpeg_fp = shutil.which(ffmpeg_fp or g_ffmpeg_fp)
    g_mkvmerge_fp = shutil.which(mkvmerge_fp or g_mkvmerge_fp)
    mkv_dir = os.path.abspath(mkv_dir)
    mpls_dir = os.path.abspath(mpls_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    if logger_fp is None:
        logger_fp = os.path.join(output_dir, 'mpls_merger.log')
    logger = get_logger(logger_fp)
    for mpls_fn in os.listdir(mpls_dir):
        if not mpls_fn.endswith('.mpls'):
            continue
        mpls_fp = os.path.join(mpls_dir, mpls_fn)
        if not os.path.isfile(mpls_fp):
            continue
        mmg(mpls_fp, mkv_dir, output_dir, logger)
    g_ffmpeg_fp = 'ffmpeg'
    g_mkvmerge_fp = 'mkvmerge'
