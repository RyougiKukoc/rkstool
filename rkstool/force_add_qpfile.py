import os
import glob
import shutil


def addqpfile(dir: str, qp_ext: str = '.24.qpfile', accept_ext = ['.m2ts']):
    dir = os.path.abspath(dir)
    for fn in os.listdir(dir):
        fp = os.path.join(dir, fn)
        if os.path.isdir(fp):
            addqpfile(fp)
            continue
        name, ext = os.path.splitext(fn)
        if ext not in accept_ext:
            continue
        tar_qp_fp = os.path.join(dir, name + qp_ext)
        res_qp_fp = os.path.join(dir, name + '.qpfile')
        if os.path.exists(tar_qp_fp):
            if tar_qp_fp != res_qp_fp:
                os.rename(tar_qp_fp, res_qp_fp)
        else:
            with open(res_qp_fp, 'w') as qpf:
                qpf.write('0 K')
        query = os.path.join(dir, name + '*.qpfile')
        for waste_qpfile in glob.glob(query):
            waste_dir = os.path.join(dir, 'waste_qp')
            os.makedirs(waste_dir, exist_ok=True)
            shutil.move(waste_qpfile, waste_dir)
