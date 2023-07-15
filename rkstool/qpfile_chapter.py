import os
import subprocess as sp
import xml.etree.ElementTree as xet


def GCFQP(
    vcfile: str, 
    qpfile: str,
    output_chapter: str,
    tmp_fp: str,
    ffprobe_fp: str, 
    mkvmerge_fp: str, 
):
    tmp_fp = os.path.abspath(tmp_fp)
    tmp_mkv_fp = os.path.join(tmp_fp, 'tmp.mkv')
    tmp_xml_fp = os.path.join(tmp_fp, 'tmp.xml')
    p = sp.Popen([mkvmerge_fp, '-o', tmp_mkv_fp, vcfile])
    r = p.communicate()
    with open(tmp_xml_fp, 'w') as xmlf:
        p = sp.Popen([ffprobe_fp, 
            '-hide_banner', 
            '-v', 'error', 
            '-threads', 'auto', 
            '-show_frames', 
            '-of', 'xml', 
            '-select_streams', 'v:0', 
            '-i', tmp_mkv_fp], stdout=xmlf)
        r = p.communicate()

    frames = xet.parse(tmp_xml_fp).getroot()[0]
    
    with open(qpfile, "r") as f:
        qpstr = f.readlines()
    qpstr = [i for i in qpstr if i != "\n"]
    qpstr = [i if i.endswith("\n") else i + "\n" for i in qpstr]
    qpstr = [i[:-3] for i in qpstr]
    qp = [int(i) for i in qpstr]
    
    chapter = ""
    for cid, qpx in enumerate(qp):
        if frames[qpx].attrib['key_frame'] != '1':  # todo: compatible with ffmpeg 5, 6
            raise AssertionError(f'Frame {qpx} must be a key frame while actually not.')
        atd = frames[qpx].attrib
        pts = atd.get('pts')
        if pts is None:
            pts = atd.get('pkt_pts')
        pts = int(pts)  # ms
        ms = pts % 1000
        ss = pts // 1000 % 60
        mm = pts // (1000*60) % 60
        hh = pts // (1000*60*60)
        chapter += f'CHAPTER{cid:02}={hh:02}:{mm:02}:{ss:02}.{ms:03}' + '\n'
        chapter += f'CHAPTER{cid:02}NAME=' + '\n'
        
    with open(output_chapter, "w") as f:
        f.write(chapter)
    
    w = int(frames[0].attrib['width'])
    h = int(frames[0].attrib['height'])

    os.remove(tmp_xml_fp)
    os.remove(tmp_mkv_fp)

    return w, h
