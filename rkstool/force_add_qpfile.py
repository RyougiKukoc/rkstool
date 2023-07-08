import os


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
        qp_fp = os.path.join(dir, name + qp_ext)
        if os.path.exists(qp_fp):
            continue
        with open(qp_fp, 'w') as qpf:
            qpf.write('0 K')
