import os
import datetime
import vapoursynth as vs
import subprocess as sp
from .mpls_chapter import read_mpls
from .logger import get_logger


def index(workspace_fp: str, logger_fp: str = None, ffprobe_fp: str = None):
    workspace_fp = os.path.abspath(workspace_fp)
    if logger_fp is None:
        logger_fn = datetime.datetime.now().strftime(r'%Y%m%d-%H%M%S') + '.indexer.log'
        logger_fp = os.path.join(workspace_fp, logger_fn)
    logger = get_logger(logger_fp)
    if ffprobe_fp is None:  # Already added ffprobe in system PATH
        ffprobe_fp = 'ffprobe'
    ffcmd = f'"{ffprobe_fp}" -v error -threads auto -show_frames -select_streams v:0 -i'

    for bd in os.listdir(workspace_fp):
        tar_fp = os.path.join(workspace_fp, bd)
        if os.path.isdir(tar_fp):
            logger.info(f'Generating qpfiles for {bd}...')
            read_mpls(tar_fp, logger=logger)
            stream_fp = os.path.join(tar_fp, 'BDMV', 'STREAM')
            for m2ts in os.listdir(stream_fp):
                if m2ts.endswith('.m2ts'):
                    logger.info(f'Indexing {bd}: {m2ts}...')
                    nvs = False  # No video stream
                    mfp = os.path.join(stream_fp, m2ts)
                    try:
                        vs.core.lsmas.LWLibavSource(mfp)
                    except vs.Error:
                        nvs = True
                        with open(os.path.join(stream_fp, m2ts + '.vserr'), 'w') as nvsf:
                            nvsf.write('No video stream.')
                    if nvs:
                        logger.info(f'No video stream in {bd}: {m2ts}, skip.')
                    else:
                        logger.info('Done, now decoding...')
                        p = sp.Popen(f'{ffcmd} "{mfp}"', stdout=sp.DEVNULL, stderr=sp.PIPE)
                        err = p.communicate()[1].decode()
                        if len(err) > 0:
                            with open(os.path.join(stream_fp, m2ts + '.vserr'), 'w') as nvsf:
                                nvsf.write('Decoding error.')
                            logger.info('Error occurs when decoding:')
                            logger.info(err)
                        else:
                            logger.info(f'Decode {bd}: {m2ts} successfully.')
                            