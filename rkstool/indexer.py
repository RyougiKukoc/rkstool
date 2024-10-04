import os
import shutil
import datetime
import subprocess as sp
from .mpls_chapter import read_mpls
from .logger import get_logger


def index(
    workspace_fp: str, 
    qponly: bool = False,
    logger_fp: str = None, 
    ffmpeg_fp: str = 'ffmpeg', 
):
    workspace_fp = os.path.abspath(workspace_fp)
    ffmpeg_fp = shutil.which(ffmpeg_fp)
    
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

    for bd in os.listdir(workspace_fp):
        tar_fp = os.path.join(workspace_fp, bd)
        if os.path.isdir(tar_fp):
            stream_fp = os.path.join(tar_fp, 'BDMV', 'STREAM')
            donemark = os.path.join(stream_fp, 'index.done')
            if not os.path.exists(stream_fp):
                continue
            if os.path.exists(donemark):
                continue
            logger.info(f'Generating qpfiles for {bd} ...')
            read_mpls(tar_fp, logger=logger)
            if qponly:
                continue
            for m2ts in os.listdir(stream_fp):
                if m2ts.endswith('.m2ts'):
                    logger.info(f'Decoding {bd}///{m2ts} ...')
                    err_fp = os.path.join(stream_fp, m2ts + '.vserr')
                    mfp = os.path.join(stream_fp, m2ts)
                    p = sp.Popen(
                        [ffmpeg_fp, 
                         '-i', mfp, 
                         '-v', 'error', 
                         '-f', 'yuv4mpegpipe', 
                         '-strict', '-1', 
                         '-'], 
                        stdout=sp.DEVNULL,
                        stderr=sp.PIPE,
                    )
                    err = p.communicate()[1].decode()
                    if len(err) > 0:
                        with open(err_fp, 'w') as ef:
                            ef.write(err)
                        logger.info(f'Error occurs when decoding {bd}///{m2ts}:')
                        logger.info(err)
                    else:
                        if os.path.exists(err_fp):
                            os.remove(err_fp)
                        logger.info(f'{bd}///{m2ts} decoded successfully!\n')
            with open(donemark, 'w') as dmf:
                dmf.write('Decoded.')
                            