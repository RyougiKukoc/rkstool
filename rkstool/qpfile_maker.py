import os
import shutil


def make_qpfile(
    dir: str, 
    qp_ext: str = '.24.qpfile', 
    force: bool = False,  # whether to cover existed '*.qpfile'
):
    dir = os.path.abspath(dir)
    for fn in os.listdir(dir):
        fp = os.path.join(dir, fn)
        if os.path.isdir(fp):
            make_qpfile(fp, qp_ext, force)
            continue
        name, ext = os.path.splitext(fn)
        if ext not in ['.m2ts']:
            continue
        waste_dir = os.path.join(dir, 'waste_qp')
        tar_qp_fp = os.path.join(dir, name + qp_ext)
        res_qp_fp = os.path.join(dir, name + '.qpfile')
        if os.path.exists(res_qp_fp) and not force:
            continue
        if os.path.exists(tar_qp_fp):
            if tar_qp_fp != res_qp_fp:
                if os.path.exists(res_qp_fp):
                    os.makedirs(waste_dir, exist_ok=True)
                    shutil.move(res_qp_fp, waste_dir)
                os.rename(tar_qp_fp, res_qp_fp)
        else:
            with open(res_qp_fp, 'w') as qpf:
                qpf.write('0 K')
