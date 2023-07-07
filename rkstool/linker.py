import os


def create_link(relative_path: str, ofp: str, lfp: str):
    fp = os.path.join(ofp, relative_path)
    for fn in os.listdir(fp):
        tar_fp = os.path.join(fp, fn)
        if os.path.isfile(tar_fp):
            os.link(tar_fp, os.path.join(lfp, relative_path, fn))
        else:
            os.makedirs(os.path.join(lfp, relative_path, fn), exist_ok=False)
            create_link(os.path.join(relative_path, fn), ofp, lfp)


def link(workspace_fp: str):
    workspace_fp = os.path.abspath(workspace_fp)
    link_workspace_fp = workspace_fp + '_link'
    linkid = 0
    while True:
        if not os.path.exists(link_workspace_fp):
            os.makedirs(link_workspace_fp, exist_ok=False)
            break
        else:
            linkid += 1
            link_workspace_fp = workspace_fp + f'_link{linkid}'
    create_link("", workspace_fp, link_workspace_fp)
