import os
import glob


def map_config(
    config_fp: str, 
    config_ext = '.vpy',
    target_fp: str | list = None, 
    replace: bool = False, 
    accept_ext = ['.m2ts'], 
):
    config_fp = os.path.abspath(config_fp)
    assert os.path.isfile(config_fp)
    with open(config_fp, 'r') as conf:
        lines = conf.readlines()
    dir_fp = os.path.dirname(config_fp)
    if target_fp is None:
        target_fp = [dir_fp]
    elif isinstance(target_fp, str):
        target_fp = [os.path.abspath(target_fp)]
    else:
        assert hasattr(target_fp, '__iter__')
        target_fp = [os.path.abspath(d) for d in target_fp]
    target_list = []
    for d in target_fp:
        for ext in accept_ext:
            target_list += glob.glob(os.path.join(glob.escape(d), '*' + ext))
    for target_fp in target_list:
        target_fn = os.path.basename(target_fp)
        name = os.path.splitext(target_fn)[0]
        script_fn = os.path.join(dir_fp, name + config_ext)
        if os.path.exists(script_fn):
            if not replace:
                continue
            else:
                os.remove(script_fn)  # for safety
        with open(script_fn, 'w') as sf:
            for line in lines:
                sf.write(line.replace('$src', target_fn).replace('$bas', name))
                