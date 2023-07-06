import os
import shutil
import datetime
import subprocess as sp
from .mpls_chapter import read_mpls
from .logger import get_logger


def index(workspace_fp: str, logger_fp: str = None, ffmpeg_fp: str = None):
    workspace_fp = os.path.abspath(workspace_fp)
    if os.path.exists(os.path.join(workspace_fp, 'BDMV', 'STREAM')):  # single volume optim
        bdid = 1
        while True:
            new_dir = os.path.join(workspace_fp, f'BD{bdid}')
            if not os.path.exists(new_dir):
                ld = os.listdir(workspace_fp)
                os.makedirs(new_dir)
                for fd in ld:
                    shutil.move(os.path.join(workspace_fp, fd), new_dir)
                break
            else:
                bdid += 1
    if logger_fp is None:
        logger_fn = 'index.' + datetime.datetime.now().strftime(r'%Y%m%d%H%M%S') + '.log'
        logger_fp = os.path.join(workspace_fp, logger_fn)
    logger = get_logger(logger_fp)
    if ffmpeg_fp is None:  # Already added ffmpeg in system PATH
        ffmpeg_fp = 'ffmpeg'

    for bd in os.listdir(workspace_fp):
        tar_fp = os.path.join(workspace_fp, bd)
        if os.path.isdir(tar_fp):
            logger.info(f'Generating qpfiles for {bd} ...')
            read_mpls(tar_fp, logger=logger)
            stream_fp = os.path.join(tar_fp, 'BDMV', 'STREAM')
            for m2ts in os.listdir(stream_fp):
                if m2ts.endswith('.m2ts'):
                    logger.info(f'Decoding {bd}///{m2ts} ...')
                    mfp = os.path.join(stream_fp, m2ts)
                    p = sp.Popen(
                        [ffmpeg_fp, 
                         '-i', mfp, 
                         '-v', 'error', 
                         '-f', 'yuv4mpegpipe', 
                         '-'], 
                        stdout=sp.DEVNULL,
                        stderr=sp.PIPE,
                    )
                    err = p.communicate()[1].decode()
                    if len(err) > 0:
                        with open(os.path.join(stream_fp, m2ts + '.vserr'), 'w') as ef:
                            ef.write(err)
                        logger.info(f'Error occurs when decoding {bd}///{m2ts}:')
                        logger.info(err)
                    else:
                        logger.info(f'{bd}///{m2ts} decoded successfully!\n')
                            