import os
import subprocess as sp
import shutil


g_mkvinfo_fp = 'mkvinfo'
g_mkvmerge_fp = 'mkvmerge'
g_mkvextract_fp = 'mkvextract'
g_qaac_fp = 'qaac'


def flac_to_aac(
    fp: str,
    keep_flac_tracks: tuple = (0,),
    # TODO: convert_mode: str = 'qaac',
    encode_params: tuple = ('-V', '127', '--no-delay'),
    trash_subdir: str = 'flac2aac_src'
):
    os.chdir(os.path.dirname(fp))
    if isinstance(keep_flac_tracks, int):
        keep_flac_tracks = [keep_flac_tracks]
    elif not hasattr(keep_flac_tracks, '__iter__'):
        raise NotImplementedError
    p = sp.Popen([g_mkvinfo_fp, '--ui-language', 'en', fp], stdout=sp.PIPE, stderr=sp.PIPE)
    mkvinfo = p.communicate()[0].decode()
    aids, alans, atns = [], [], []
    track_start, tid, lan, tn = False, None, 'und', ''
    for line in mkvinfo.splitlines():
        if not track_start:
            if 'track ID for mkvmerge & mkvextract' in line:
                track_start = True
                tid = line.split('track ID for mkvmerge & mkvextract: ')[-1].rstrip(')')
            else:
                continue
        else:
            if line.startswith('|  + Track type: ') and 'audio' not in line:
                track_start, tid, lan, tn = False, None, 'und', ''
            elif line.startswith('+') or line.startswith('|+') or line.startswith('| +'):
                aids.append(tid)
                alans.append(lan)
                atns.append(tn)
                track_start, tid, lan, tn = False, None, 'und', ''
            elif line.startswith('|  + Codec ID: ') and 'A_FLAC' not in line:
                return
            elif line.startswith('|  + Language: '):
                lan = line[15:].rstrip()
            elif line.startswith('|  + Name: '):
                tn = line[11:].rstrip()
    if len(keep_flac_tracks) >= len(aids):
        return
    src_audstr = 'FLAC' if len(aids) == 1 else 'FLACx' + str(len(aids))
    dst_audstr = ''
    if len(keep_flac_tracks) > 1:
        dst_audstr += f'FLACx{len(keep_flac_tracks)} '
    elif len(keep_flac_tracks) == 1:
        dst_audstr += 'FLAC '
    if len(aids) - len(keep_flac_tracks) > 1:
        dst_audstr += f'AACx{len(aids) - len(keep_flac_tracks)}'
    else:
        dst_audstr += 'AAC'
    dst_fp = os.path.join(os.path.dirname(fp), os.path.basename(fp).replace(src_audstr, dst_audstr))
    if os.path.exists(dst_fp):
        return
    extract_cmd = [g_mkvextract_fp, fp, 'tracks']
    for aid in aids:
        extract_cmd.append(f'{aid}:_tmp_{aid}.flac')
    _ = sp.run(extract_cmd)
    merge_cmd = [g_mkvmerge_fp, '-o', dst_fp, '--no-audio', fp]
    keep_aids = [aids[i] for i in keep_flac_tracks]
    for aid, lan, tn in zip(aids, alans, atns):
        merge_cmd += ['--language', f'0:{lan}', '--track-name', f'0:{tn}']
        if aid in keep_aids:
            merge_cmd.append(f'_tmp_{aid}.flac')
        else:
            _ = sp.run([g_qaac_fp, '-o', f'_tmp_{aid}.aac'] + list(encode_params) + [f'_tmp_{aid}.flac'])
            merge_cmd.append(f'_tmp_{aid}.aac')
    _ = sp.run(merge_cmd)
    for aid in aids:
        os.remove(f'_tmp_{aid}.flac')
        if aid not in keep_aids:
            os.remove(f'_tmp_{aid}.aac')
    trash_subdir_fp = os.path.join(os.path.dirname(fp), trash_subdir)
    os.makedirs(trash_subdir_fp, exist_ok=True)
    shutil.move(fp, os.path.join(trash_subdir_fp, os.path.basename(fp)))


def flac2aac(
    workspace_fp: str,
    keep_flac_tracks: tuple = (0,),
    # TODO: convert_mode: str = 'qaac',
    encode_params: tuple = ('-V', '127', '--no-delay'),
    trash_subdir: str = 'flac2aac_src',
    mkvinfo_fp = None,
    mkvmerge_fp = None,
    mkvextract_fp = None,
    qaac_fp = None,
):
    global g_mkvinfo_fp, g_mkvmerge_fp, g_mkvextract_fp, g_qaac_fp
    path_record = os.path.abspath('.')
    g_mkvinfo_fp = shutil.which(mkvinfo_fp or g_mkvinfo_fp)
    g_mkvmerge_fp = shutil.which(mkvmerge_fp or g_mkvmerge_fp)
    g_mkvextract_fp = shutil.which(mkvextract_fp or g_mkvextract_fp)
    g_qaac_fp = shutil.which(qaac_fp or g_qaac_fp)
    for dirpath, dirnames, filenames in os.walk(workspace_fp):
        if os.path.basename(dirpath) == trash_subdir:
            continue
        for fn in filenames:
            if not fn.endswith('.mkv'):
                continue
            flac_to_aac(
                fp=os.path.join(dirpath, fn),
                keep_flac_tracks=keep_flac_tracks,
                encode_params=encode_params,
                trash_subdir=trash_subdir,
            )
    g_mkvinfo_fp = 'mkvinfo'
    g_mkvmerge_fp = 'mkvmerge'
    g_mkvextract_fp = 'mkvextract'
    g_qaac_fp = 'qaac'
    os.chdir(path_record)
    