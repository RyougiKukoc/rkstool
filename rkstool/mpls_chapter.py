# Stolen from YomikoR
from typing import Dict, Set, List, Optional
import io
import os
import re
from struct import unpack
from functools import partial
from math import ceil, floor
import logging


__all__ = [
    'read_mpls',
]


def parse_milliseconds(full_ms: int) -> str:
    '''
    HH:MM:SS.MIL format
    '''
    ms = full_ms % 1000
    full_secs = full_ms // 1000
    secs = full_secs % 60
    full_mins = full_secs // 60
    mins = full_mins % 60
    hours = full_mins // 60
    return f'{hours:02}:{mins:02}:{secs:02}.{ms:03}'


def time_to_chapter_ogg(time_strs: List[str]) -> str:
    ''' CHAPTER01=00:00:00.000
        CHAPTER01NAME=
        CHAPTER02=00:01:31.132
        CHAPTER02NAME=
        ......
    '''
    return_str = ''
    for n, time_str in enumerate(time_strs):
        idx = n + 1
        return_str = return_str + f'CHAPTER{idx:02}={time_str}' + '\n'
        return_str = return_str + f'CHAPTER{idx:02}NAME=' + '\n'
    return return_str


def time_to_chapter_xml(time_strs: List[str], language_str: str = 'jpn') -> str:
    ''' XML stuffs (preferred)
    '''
    return_str = f'<?xml version="1.0"?>' + '\n'
    return_str = return_str + r'<!-- <!DOCTYPE Chapters SYSTEM "matroskachapters.dtd"> -->' + '\n'
    return_str = return_str + r'<Chapters>' + '\n' + r'<EditionEntry>' + '\n'
    for time_str in time_strs:
        return_str = return_str + r'<ChapterAtom>' + '\n' + r'<ChapterDisplay>' + '\n'
        return_str = return_str + r'<ChapterString></ChapterString>' + '\n'
        return_str = return_str + r'<ChapterLanguage>' + language_str + r'</ChapterLanguage>' + '\n'
        return_str = return_str + r'</ChapterDisplay>' + '\n'
        return_str = return_str + r'<ChapterTimeStart>' + time_str + r'</ChapterTimeStart>' + '\n'
        return_str = return_str + r'</ChapterAtom>' + '\n'
    return_str = return_str + r'</EditionEntry>' + '\n' + r'</Chapters>'
    return return_str


def frames_to_qpfile(frames: List[int]) -> str:
    return_str = ''
    for frame in frames:
        return_str = return_str + f'{frame} K' + '\n'
    return return_str


def f_skip(f: io.BufferedReader, length: int) -> None:
    f.seek(f.tell() + length)


def f_get(f: io.BufferedReader, length: int) -> int:
    '''
    In BD there are unsigned types in big-endian
    '''
    if length == 1:
        ret, = unpack('>B', f.read(length))
        return ret
    elif length == 2:
        ret, = unpack('>H', f.read(length))
        return ret
    elif length == 4:
        ret, = unpack('>I', f.read(length))
        return ret
    elif length == 8:
        ret, = unpack('>Q', f.read(length))
        return ret
    else:
        raise ValueError('f_get: cannot unpack data with given size.')


BD_VideoFormat: Dict[int, str] = {
    1: '480i',
    2: '576i',
    3: '480p',
    4: '1080i',
    5: '720p',
    6: '1080p',
    7: '576p',
    8: '2160p'
}


BD_FrameRate: Dict[int, float] = {
    1: 24000 / 1001,
    2: 24.0,
    3: 25.0,
    4: 30000 / 1001,
    6: 50.0,
    7: 60000 / 1001,
}


class StreamInfo:
    def __init__(self, FileName: str, VideoFormat: int, FrameRate: int) -> None:
        self.file_name = FileName
        self.video_format = BD_VideoFormat[VideoFormat]
        self.video_format_index = VideoFormat
        self.frame_rate_index = FrameRate
        self.timestamps: Set[int] = set()
        self.timestamps_sorted: Optional[List[int]] = None

    def sort_timestamps(self, align_as_120: bool = True) -> None:
        ts_sorted = sorted(self.timestamps)
        self.timestamps_sorted = [ts - ts_sorted[0] for ts in ts_sorted]
        # Align as 120000 / 1001 fps in case of any future VFR post-processing
        if self.frame_rate_index in {1, 4, 7} and align_as_120:
            self.timestamps_sorted = [ceil(floor(ts / 45000 * 120000 / 1001 + 0.5) * 375.375) for ts in self.timestamps_sorted]

    def prepare(self, min_length: int = 1, align_as_120: bool = True) -> bool:
        if len(self.timestamps) < min_length:
            return False
        elif self.timestamps_sorted is None:
            self.sort_timestamps(align_as_120)
            return True
        else:
            return True

    def get_key_frames(self, frame_rate: float) -> List[int]:
        return [floor(ts / 45000 * frame_rate + 0.5) for ts in self.timestamps_sorted]

    def get_milliseconds(self) -> List[int]:
        return [ceil(ts / 45) for ts in self.timestamps_sorted]

    def gen_qpfile(self, frame_rate: Optional[float] = None) -> str:
        if frame_rate is None:
            frame_rate = BD_FrameRate[self.frame_rate_index]
        key_frames = self.get_key_frames(frame_rate)
        return frames_to_qpfile(key_frames)

    def gen_chapter_ogg(self) -> str:
        mil_strs = [parse_milliseconds(ms) for ms in self.get_milliseconds()]
        return time_to_chapter_ogg(mil_strs)

    def gen_chapter_xml(self, language: str = 'jpn') -> str:
        mil_strs = [parse_milliseconds(ms) for ms in self.get_milliseconds()]
        return time_to_chapter_xml(mil_strs, language)


def parse_mpls(mpls: str, streams: Dict[str, StreamInfo]) -> None:
    ''' Read a MPLS file and save timestamps in entries of streams
        Reference: https://github.com/lw/BluRay/wiki/MPLS
    '''
    # Streams in this MPLS, indexed starting from 0
    mpls_streams: Dict[int, StreamInfo] = dict()
    with open(mpls, 'rb') as f:
        fskip = partial(f_skip, f)
        fget = partial(f_get, f)

        # Begin
        assert f.read(4).decode() == 'MPLS'
        fskip(4)
        PlayListStartAddress = fget(4)
        PlayListMarkStartAddress = fget(4)

        # Playlist, get names (of M2TS) and video info
        f.seek(PlayListStartAddress)
        fskip(6)
        NumberOfPlayItems = fget(2)
        fskip(2)
        for stream_idx in range(NumberOfPlayItems):
            # Check if it contains a valid first-track video
            fskip(2)
            FileName = f.read(5).decode()
            fskip(27)
            # Enter STN table
            STN_Length = fget(2)
            STN_Start = f.tell()
            fskip(14)
            StreamEntry_Length = fget(1)
            fskip(StreamEntry_Length)
            fskip(1)
            StreamCodingType = fget(1)
            if StreamCodingType in {0x01, 0x02, 0x1B, 0xEA, 0x24}:
                # Then it's a video (but not in MVC format)
                b = fget(1)
                VideoFormat = b >> 4
                FrameRate = b - (VideoFormat << 4)
                try:
                    if FileName in streams.keys():
                        mpls_streams[stream_idx] = streams[FileName]
                    else:
                        stream = StreamInfo(FileName, VideoFormat, FrameRate)
                        streams[FileName] = stream
                        mpls_streams[stream_idx] = stream
                except KeyError:
                    pass
            # After visiting the first track, leave
            f.seek(STN_Start + STN_Length)

        # Playlist Marks, get timestamps
        f.seek(PlayListMarkStartAddress)
        fskip(4)
        NumberOfPlayListMarks = fget(2)
        for _ in range(NumberOfPlayListMarks):
            fskip(2)
            PlayItemID = fget(2)
            TimeStamp = fget(4)
            mpls_streams[PlayItemID].timestamps.add(TimeStamp)
            fskip(6)


def get_logger(log_fp: str, logger_name: str = 'inspector'):
    import logging

    logger = logging.getLogger(logger_name)
    sh = logging.StreamHandler()
    fh = logging.FileHandler(log_fp, mode='a')
    fmt = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    logger.setLevel(logging.INFO)
    sh.setLevel(logging.INFO)
    fh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    fh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger


def read_mpls(
        bd_dir: str, 
        output_dir: Optional[str] = None, 
        min_length: int = 0, 
        logger_fp: str = None, 
):
    bd_dir = os.path.abspath(bd_dir)
    if os.path.isfile(bd_dir):
        if os.path.splitext(bd_dir)[1] in ('.m2ts', '.mpls'):
            bd_dir = os.path.abspath(os.path.join(bd_dir, os.path.pardir, os.path.pardir, os.path.pardir))
        else:
            raise TypeError('Input file type not supported.')
    mpls_dir = os.path.join(bd_dir, 'BDMV', 'PLAYLIST')
    if not os.path.isdir(mpls_dir):
        raise ValueError('Input dir is not valid.')
    if logger_fp is None:
        logger_fp = bd_dir + '.log'
    logger = get_logger(logger_fp)

    # Init stream dict info
    streams: Dict[str, StreamInfo] = dict()
    # Parse each MPLS
    p = re.compile('[0-9][0-9][0-9][0-9][0-9].mpls')
    for mpls in os.listdir(mpls_dir):
        if p.match(mpls):
            parse_mpls(os.path.join(mpls_dir, mpls), streams)

    # Prepare
    exclude_list = []
    for idx_str, stream in streams.items():
        if not stream.prepare(min_length):
            exclude_list.append(idx_str)
    for idx_str in exclude_list:
        del streams[idx_str]

    # Output
    if len(streams.keys()) < 1:
        logger.info('No chapter found')
    else:
        if output_dir is None:
            output_dir = os.path.join(bd_dir, 'BDMV', 'STREAM')
        os.makedirs(output_dir, exist_ok=True)
        info_str = 'Generated qpfiles for '
        for idx_str, stream in streams.items():
            # Write chapter in OGG
            with open(os.path.join(output_dir, idx_str + '.chapter.txt'), 'w') as outf:
                outf.write(stream.gen_chapter_ogg())
            # Write qpfile but exclude the most trivial ones (with only frame zero)
            if len(stream.timestamps) < 2:
                continue
            if stream.frame_rate_index in {2, 3, 6}: # 24, 25, 50
                with open(os.path.join(output_dir, idx_str + '.qpfile'), 'w') as outf:
                    outf.write(stream.gen_qpfile())
            elif stream.frame_rate_index == 1: # 23.976
                with open(os.path.join(output_dir, idx_str + '.24.qpfile'), 'w') as outf:
                    outf.write(stream.gen_qpfile())
            else: # 29.97 or 59.94
                with open(os.path.join(output_dir, idx_str + '.24.qpfile'), 'w') as outf:
                    outf.write(stream.gen_qpfile(frame_rate=BD_FrameRate[1]))
                with open(os.path.join(output_dir, idx_str + '.30.qpfile'), 'w') as outf:
                    outf.write(stream.gen_qpfile(frame_rate=BD_FrameRate[4]))
                with open(os.path.join(output_dir, idx_str + '.60.qpfile'), 'w') as outf:
                    outf.write(stream.gen_qpfile(frame_rate=BD_FrameRate[7]))
            info_str = info_str + idx_str + ' '
        logger.info(info_str)
