import os
import glob
import shutil


def simplesort(tosort_fp: str, acceptext: list = ['.m2ts']):
    tosort_fp = os.path.abspath(tosort_fp)
    for fn in os.listdir(tosort_fp):
        target_fp = os.path.join(tosort_fp, fn)
        if os.path.isfile(target_fp):
            continue
        for tomove in os.listdir(target_fp):
            n, e = os.path.splitext(tomove)
            if e not in acceptext:
                continue
            query = os.path.join(tosort_fp, n + '*')
            for qres in glob.glob(query):
                shutil.move(qres, os.path.join(target_fp, os.path.basename(qres)))
