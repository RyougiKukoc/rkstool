def GCFQP(
    vcfile: str, 
    qpfile: str,
    output_chapter: str
):
    import xml.etree.ElementTree as xet
    import os
    
    os.system(f'mkvmerge -o tmp.mkv "{vcfile}"')
    os.system('ffprobe -hide_banner -v error -threads auto -show_frames -of xml -select_streams v:0 -i tmp.mkv > tmp.xml')
    frames = xet.parse("tmp.xml").getroot()[0]
    
    with open(qpfile, "r") as f:
        qpstr = f.readlines()
    qpstr = [i for i in qpstr if i != "\n"]
    qpstr = [i if i.endswith("\n") else i + "\n" for i in qpstr]
    qpstr = [i[:-3] for i in qpstr]
    qp = [int(i) for i in qpstr]
    
    chapter = ""
    for cid, qpx in enumerate(qp):
        if frames[qpx].attrib['key_frame'] != '1':
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
    
    os.remove("tmp.mkv")
    os.remove("tmp.xml")