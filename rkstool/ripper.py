import os
import runpy
import datetime
from vapoursynth import core
from .logger import get_logger, Logger


def dfs(
    rip_path: str,
    recursion: bool = True, 
    vc_ext: str = '.hevc',
    run_ext: str = '.py', 
    accept_ext: list = ['.m2ts'],
    run_name: str = '__main__',
    logger: Logger = None, 
):
    for fn in os.listdir(rip_path):
        tar_fp = os.path.join(rip_path, fn)
        if os.path.isdir(tar_fp):
            if recursion:
                dfs(
                    rip_path=tar_fp,
                    recursion=recursion,
                    vc_ext=vc_ext,
                    run_ext=run_ext,
                    accept_ext=accept_ext,
                    run_name=run_name,
                    logger=logger,
                )
            continue
        name, ext = os.path.splitext(fn)
        if ext not in accept_ext:
            continue
        rpy_fp = os.path.join(rip_path, name + run_ext)
        if not os.path.exists(rpy_fp):
            continue
        vc_fp = os.path.join(rip_path, name + vc_ext)
        busy_fp = vc_fp + '.busy'
        break_fp = vc_fp + '.break'
        if os.path.exists(vc_fp) and not os.path.exists(break_fp):
            continue
        with open(busy_fp, 'w') as busyf:
            busyf.write(f'{vc_fp} is being encoded.')
        runpy.run_path(rpy_fp, run_name=run_name)
        if os.path.exists(busy_fp):
            os.remove(busy_fp)
        if not os.path.exists(vc_fp):  # spj for a unusual script
            continue
        ori_frames = core.lsmas.LWLibavSource(tar_fp).num_frames
        rip_frames = core.lsmas.LWLibavSource(vc_fp).num_frames
        if ori_frames != rip_frames:
            logger.warning('Number of frames cannot match!')
            logger.info(f'{tar_fp}: {ori_frames}')
            logger.info(f'{vc_fp}: {rip_frames}')
            with open(break_fp, 'w') as breakf:
                breakf.write(f'{tar_fp}: {ori_frames}\n{vc_fp}: {rip_frames}')
        else:
            if os.path.exists(break_fp):
                logger.info(f'{vc_fp} re-encoded successfully!')
                os.remove(break_fp)
        

def rip(
    rip_path: str,
    recursion: bool = True, 
    vc_ext: str = '.hevc',
    run_ext: str = '.py', 
    accept_ext: list = ['.m2ts'],
    run_name: str = '__main__',
    logger = None, 
    logger_fp: str = None,
    num_redo: int = 1,
):
    assert type(num_redo) == int
    rip_path = os.path.abspath(rip_path)
    if logger is None:
        if logger_fp is None:
            logger_fn = 'rip.' + datetime.datetime.now().strftime(r'%Y%m%d%H%M%S') + '.log'
            logger_fp = os.path.join(rip_path, logger_fn)
        logger = get_logger(logger_fp)
    dfs(
        rip_path=rip_path,
        recursion=recursion,
        vc_ext=vc_ext,
        run_ext=run_ext,
        accept_ext=accept_ext,
        run_name=run_name,
        logger=logger,
    )
    while num_redo > 0:
        num_redo -= 1
        logger.info('-' * 50)
        logger.info('Re-encoding break files ...')
        dfs(
            rip_path=rip_path,
            recursion=recursion,
            vc_ext=vc_ext,
            run_ext=run_ext,
            accept_ext=accept_ext,
            run_name=run_name,
            logger=logger,
        )
    logger.info('Done.')
