import subprocess as sp
import os
import shutil
import xml.etree.ElementTree as xet
from typing import Union, Tuple

def cut_mkv(
    src_fp: str,
    chapters: Union[str, Tuple[int]],
    tar_dir: str = None,
    ffmpeg_fp: str = 'ffmpeg',
    mkvmerge_fp: str = 'mkvmerge',
    mkvextract_fp: str = 'mkvextract'
):
    ffmpeg_fp = shutil.which(ffmpeg_fp)
    mkvmerge_fp = shutil.which(mkvmerge_fp)
    mkvextract_fp = shutil.which(mkvextract_fp)
    src_fp = os.path.abspath(src_fp)
    tar_dir = os.path.dirname(src_fp) if tar_dir is None else os.path.abspath(tar_dir)
    os.makedirs(tar_dir, exist_ok=True)
    path_record = os.path.abspath('.')
    os.chdir(tar_dir)

    extract_cmd = [mkvextract_fp, src_fp, 'chapters', '_chapter.xml', 'tracks']
    audio_count = 0
    p = sp.Popen([mkvmerge_fp, '-i', src_fp], stdout=sp.PIPE, stderr=sp.PIPE)
    mkvinfo = p.communicate()[0].decode()
    for line in mkvinfo.splitlines():
        if 'audio' in line:
            if '(FLAC)' not in line:
                print(f'{src_fp} {line} is not a FLAC audio track!')
                return
            else:
                audio_count += 1
            extract_cmd += [f'{audio_count}:_a{audio_count}.flac']
    _ = sp.run(extract_cmd)

    chapter_list = []
    fpb_root = xet.parse('_chapter.xml').getroot()
    for ca in fpb_root.find('EditionEntry').findall('ChapterAtom'):
        chapter_list.append(ca.find('ChapterTimeStart').text)
    num_chapters = len(chapter_list)

    chapter_str = 'chapters:'
    if isinstance(chapters, str):
        assert chapters.lower() == 'all'
        chapter_str += 'all'
        chapters = list(range(num_chapters))
    elif hasattr(chapters, '__iter__'):
        chapters = [num_chapters + item for item in chapters if item < 0]
        assert all(isinstance(item, int) and item >= 0 for item in chapters)
        chapters = sorted(list(set(chapters)))
        chapter_str += ','.join(str(item + 1) for item in chapters)  # mkvmerge counts chapters from 1
    else:
        print('Unsupported chapters format: ', chapters)
        return
    if not chapter_list[0].startswith('00:00:00.000'):
        chapter_list = ['00:00:00.000000000'] + chapter_list
        num_chapters += 1
        chapters = [item + 1 for item in chapters]
    if chapters[0] != 0:
        chapters = [0] + chapters
    num_intervals = len(chapters)
    # In general, the last interval is from the last chapter to the end of video

    src_fn = os.path.splitext(os.path.basename(src_fp))[0]
    formatter = f'%0{len(str(num_intervals))}d'
    if src_fn.endswith(')'):
        tar_fn = '('.join(src_fn.split('(')[:-1]) + \
            f'- {formatter} (' \
            + src_fn.split(')')[-2].split('(')[-1] + ').mkv'
    else:
        tar_fn = src_fn + f' - {formatter}.mkv'
    tar_fn = '[pre] ' + tar_fn
    
    _ = sp.run([mkvmerge_fp, '-o', tar_fn, '-A', '--split', chapter_str, src_fp])

    for i, chapter in enumerate(chapters, 1):
        tar_seg = tar_fn % i
        out_seg = tar_seg[6:]
        merge_cmd = [mkvmerge_fp, '-o', out_seg, tar_seg]
        for aid in range(audio_count):
            track_fp = f'_a{aid+1}.flac'
            split_fp = f'_a{aid+1}_{i}.flac'
            split_cmd = [ffmpeg_fp, '-i', track_fp, '-ss', chapter_list[chapter]]
            if i < num_intervals:
                split_cmd += ['-to', chapter_list[chapters[i]]]
            split_cmd += ['-compression_level', '12', '-y']
            split_cmd.append(split_fp)
            merge_cmd.append(split_fp)
            _ = sp.run(split_cmd)
        _ = sp.run(merge_cmd)

    for i, _ in enumerate(chapters, 1):
        tar_seg = tar_fn % i
        os.remove(tar_seg)
        for aid in range(audio_count):
            split_fp = f'_a{aid+1}_{i}.flac'
            os.remove(split_fp)
    for aid in range(audio_count):
        os.remove(f'_a{aid+1}.flac')
    os.remove('_chapter.xml')
    os.chdir(path_record)
