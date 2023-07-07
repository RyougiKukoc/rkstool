import os


def collect(workspace_fp: str):
    workspace_fp = os.path.abspath(workspace_fp)
    bd_list = os.listdir(workspace_fp)

    target_fp = os.path.join(workspace_fp, '#Collection')
    colid = 0
    while True:
        if not os.path.exists(target_fp):
            os.makedirs(target_fp, exist_ok=False)
            break
        else:
            colid += 1
            target_fp = os.path.join(workspace_fp, f'#Collection{colid}')
    
    for bd in bd_list:
        bd_fp = os.path.join(workspace_fp, bd)
        if not os.path.isdir(bd_fp):
            continue
        stream_fp = os.path.join(bd_fp, 'BDMV', 'STREAM')
        if not os.path.exists(stream_fp):
            continue
        for m2ts in os.listdir(stream_fp):
            if not m2ts.endswith('.m2ts'):
                continue
            m2ts_fp = os.path.join(stream_fp, m2ts)
            name = os.path.splitext(m2ts)[0]
            name_fp = os.path.join(stream_fp, name)
            if os.path.exists(m2ts_fp + '.vserr'):
                continue
            os.link(m2ts_fp, os.path.join(target_fp, f'{bd}_{m2ts}'))
            qpfile_prefix = ['.qpfile', '.24.qpfile', '.30.qpfile', '.60.qpfile']
            for qpfile in qpfile_prefix:
                qpfile_fp = name_fp + qpfile
                if not os.path.exists(qpfile_fp):
                    continue
                os.link(qpfile_fp, os.path.join(target_fp, f'{bd}_{name}{qpfile}'))
