import os
import glob


def _map_config_lines(
    config_str_lines: list[str], 
    config_ext = '.vpy',
    target_fp: str | list | None = None, 
    replace: bool = False, 
    accept_ext = ('.m2ts',), 
):
    """
    config_fp = os.path.abspath(config_fp)
    assert os.path.isfile(config_fp)
    with open(config_fp, 'r') as conf:
        lines = conf.readlines()
    if target_fp is None:
        dir_fp = os.path.dirname(config_fp)
        target_fp = [dir_fp]
    elif isinstance(target_fp, str):
        target_fp = [os.path.abspath(target_fp)]
    else:
        assert hasattr(target_fp, '__iter__')
        target_fp = [os.path.abspath(d) for d in target_fp]
    """
    target_list = []
    for d in target_fp:
        for ext in accept_ext:
            target_list += glob.glob(os.path.join(glob.escape(d), '*' + ext))
    for target_fp in target_list:
        target_dir = os.path.dirname(target_fp)
        target_fn = os.path.basename(target_fp)
        name = os.path.splitext(target_fn)[0]
        script_fn = os.path.join(target_dir, name + config_ext)
        if os.path.exists(script_fn):
            if not replace:
                continue
            else:
                os.remove(script_fn)  # for safety
        with open(script_fn, 'w', encoding='UTF-8') as sf:
            sf.writelines(line.replace('$src', target_fn).replace('$bas', name) for line in config_str_lines)
                

def map_config(
    config_fp: str, 
    config_ext = '.vpy',  # need not to specify if config is an ini file
    target_fp: str | list | None = None, 
    replace: bool = False, 
    accept_ext = ('.m2ts',), 
):
    config_fp = os.path.abspath(config_fp)
    assert os.path.isfile(config_fp)
    with open(config_fp, 'r', encoding='UTF-8') as conf:
        lines = conf.readlines()
    if target_fp is None:
        dir_fp = os.path.dirname(config_fp)
        target_fp = [dir_fp]
    elif isinstance(target_fp, str):
        target_fp = [os.path.abspath(target_fp)]
    else:
        assert hasattr(target_fp, '__iter__')
        target_fp = [os.path.abspath(d) for d in target_fp]
    if config_fp.lower().endswith(".ini"):
        lines_vpy, lines_py = [], []
        line_idx = 0
        sl, tl = [], []
        while line_idx < len(lines):
            line = lines[line_idx]
            if line.startswith(";"):
                if "/" in line:
                    sl.append(line_idx)
                elif len(sl) == len(tl) + 1:
                    tl.append(line_idx)
            line_idx += 1
        lines_vpy = lines[sl[0]+1: tl[0]]
        lines_py = lines[sl[1]+1: tl[1]]
        vpy_prefix = "." + lines[sl[0]].split("/")[-1].strip()
        _map_config_lines(lines_vpy, vpy_prefix, target_fp, replace, accept_ext)
        _map_config_lines(lines_py, ".py", target_fp, replace, accept_ext)
    else:
        _map_config_lines(lines, config_ext, target_fp, replace, accept_ext)
        