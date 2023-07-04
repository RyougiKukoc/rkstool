import os
import datetime
import vapoursynth as vs
from .mpls_chapter import read_mpls
from .logger import get_logger


def index(workspace_fp: str, logger_fp: str = None):
    workspace_fp = os.path.abspath(workspace_fp)
    if logger_fp is None:
        logger_fn = datetime.datetime.now().strftime(r'%Y%m%d-%H%M%S') + '.indexer.log'
        logger_fp = os.path.join(workspace_fp, logger_fn)
    logger = get_logger(logger_fp)

    for bd in os.listdir(workspace_fp):
        tar_fp = os.path.join(workspace_fp, bd)
        if os.path.isdir(tar_fp):
            logger.info(f'Generating qpfiles for {bd}...')
            read_mpls(tar_fp, logger=logger)
            stream_fp = os.path.join(tar_fp, 'BDMV', 'STREAM')
            for m2ts in os.listdir(stream_fp):
                if m2ts.endswith('.m2ts'):
                    try:
                        logger.info(f'Indexing {bd}: {m2ts}')
                        vs.core.lsmas.LWLibavSource(os.path.join(stream_fp, m2ts))
                    except vs.Error:
                        logger.info(f'{bd}: {m2ts} has no video stream!')
                        with open(os.path.join(stream_fp, m2ts + '.nvd'), 'w') as nvd:
                            nvd.write('No video stream.')
