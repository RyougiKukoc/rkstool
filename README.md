# rkstool
***The framework was originally constructed by mein Führer Alice.***

**Special Thanks to Jan, x_x.**

# 操作指北

## 环境准备
0. 将 `rkstool` 文件夹放到 Python 环境中 `Lib\site-packages` 文件夹下
1. 使用 `pip` 安装 `librosa`：`pip install librosa`。
2. 安装 [mkvmerge](https://mkvtoolnix.download/)，将安装目录（带有 `mkvmerge.exe` 的文件夹）加入系统 Path 或在实际使用中手动指定该路径。
3. 下载 [eac3to](https://forum.doom9.org/showthread.php?t=125966)、[tsmuxer](https://github.com/justdan96/tsMuxer) 和 [ffmpeg](https://github.com/BtbN/FFmpeg-Builds/releases)（暂时只支持 ffmpeg4），将包含对应可执行文件的目录加入系统 Path、或在实际使用中手动指定该路径。

## 加载工具链
在任意位置打开一个 python 控制台，输入：
```python
import rkstool as rkt
```
上述代码引入了工具链，如果没有报错说明工具链的 python 支持没有问题。工具链的每个步骤都是一个函数，比如创建硬链接副本被包装为一个 `link` 函数，由于该函数在 `rkstool` 中、而上述代码将 `rkstool` 缩写成 `rkt`，使用 `link` 函数时只需写
```python
rkt.link(some_path)
```
即可。

另一种不太推荐的操作形式是：
```python
from rkstool import *
link(some_path)
```
这将 `rkstool` 中的所有函数都暴露了出来，获得的唯一好处是你不用再写 `rkt.`。

## 创建副本
假设你的源是 P2P 下载的，在很长一段时间保种是一类刚需。此时你可以对整个源做硬链接（需要在 `NTFS` 分区中进行此操作）。为了描述方便，我们假设你的源最开始长这样：
```text
D:\P2P\[BDMV] KUBO-SAN WA MOB WO YURUSANAI
├─KUBOSAN_1
│  ├─BDMV
│  │  ├─...
│  │  └─STREAM
│  ├─...
│  └─Scans
└─KUBOSAN_2
    ├─BDMV
    │  ├─...
    │  └─STREAM
    ├─...
    └─Scans
```
运行命令：
```python
rkt.link(r"D:\P2P\[BDMV] Kubo-san wa Mob wo Yurusanai")
```
不出意外你会发现在 `D:\P2P\` 下硬链接出了一个 `[BDMV] Kubo-san wa Mob wo Yurusanai_link` 文件夹，这是我们为源创建的副本。***提示：你可以把一个文件夹从文件管理器拖到控制台上，这样能快速获取文件夹的绝对路径。当路径中存在空格时，它会自动补充一对双引号，此时只需先写一个 `r` 再将文件夹拖进来即可，python 中 `r""` 的字符串强制不转义反斜杠 `\`，更多关于路径的知识可以参考[这里](http://vapoursynth.com/doc/pythonreference.html#windows-file-paths)。当路径不存在空格时，它不会自动补充一对双引号，你需要先写 `r"`、将文件夹拖进来后再补一个 `"`。***

## 整理工作区
本环节涉及两个函数 `index` 和 `collect`。但在使用它们之前，我们需要将源结构整理成统一的格式，称为“工作区”。

工作区下需陈列一系列对齐的原盘，每个原盘对应一个子文件夹，子文件夹下面有 `BDMV`、该 `BDMV` 下有 `STREAM`。利用硬链接副本可以自由剪切粘贴（复制粘贴不行，显然）、重命名的特性，可以将上节中创建的硬链接副本整理为：
```text
D:\P2P\[BDMV] KUBO-SAN WA MOB WO YURUSANAI_LINK
├─Scans
│  ├─1
│  └─2
└─WorkSpace-Kubosan
    ├─KUBOSAN_1
    │  ├─BDMV
    │  │  ├─...
    │  │  └─STREAM
    │  └─...
    └─KUBOSAN_2
        ├─BDMV
        │  ├─...
        │  └─STREAM
        └─...
```
注意到原种中的 Scans 文件夹没有卷标，这里将其卷标打上后抽出到 Scans 文件夹下。而 BD 主体则被扔进 WorkSpace-Kubosan 子文件夹中，这即是上文所述的“工作区”。工作区中的每一卷原盘都在一个子文件夹内，该子文件夹下没有多余的嵌套。

整理好后我们对工作区中的每一部 BD 生成章节对应的 qpfile 并检查视频流，从中选择需要压制的文件并标记，方便后续的抽出。运行命令：
```python
rkt.index(r"D:\P2P\[BDMV] Kubo-san wa Mob wo Yurusanai\WorkSpace-Kubosan")
```
如果你没有将 ffmpeg 放入系统 path，上述命令需要增加一个描述 ffmpeg 位置的参数，假如你的 ffmpeg 放在 `E:\green_software\ffmpeg_4.4\bin\ffmpeg.exe`，将上述命令改成：
```python
rkt.index(r"D:\P2P\[BDMV] Kubo-san wa Mob wo Yurusanai\WorkSpace-Kubosan", ffmpeg_fp=r"E:\green_software\ffmpeg_4.4\bin\ffmpeg.exe")
```
该函数不出意外会运行很长时间。

接下来，我们将每一部 BD 中需要压制的文件及相关 qpfile 硬链接出来。运行命令：
```python
rkt.collect(r"D:\P2P\[BDMV] Kubo-san wa Mob wo Yurusanai\WorkSpace-Kubosan")
```
很快，在工作区（`WorkSpace-Kubosan` 文件夹）下生成了一个 #Collection 文件夹。文件夹内是 m2ts 文件和 qpfile 文件，并添加了来源前缀。

## 分类
在刚整理出的 #Collection 文件夹中，所有的文件都放在一起，这对批处理而言很不方便。`simple_sort` 函数提供了一个简易的分类器，它的用法如下：
1. 首先，在 #Collection 文件夹中新建子文件夹并命名；
2. 将源（比如 m2ts 文件）拖入子文件夹，不用管源的同名不同后缀文件（比如同名 qpfile）；
3. 将所有的源分类好后，运行：
```python
rkt.simple_sort(path_to_collection)
```

如果待归纳的源不是 m2ts 文件，或者多于一种文件，可以将文件后缀以列表的形式引入参数 `accept_ext` 中，比如待归纳的源有 m2ts 和 mkv 两种：
```python
rkt.simple_sort(path_to_collection, accept_ext=['.m2ts', '.mkv'])
```

## 脚本映射
每类源的处理脚本理应相同，故可以有一个通用的模板。模板的映射针对指定后缀的源，模板中对于输入源的文件名支持两种映射：
1. `$bas`: 表示对应源文件不包含后缀的文件名 (basename)
2. `$src`: 表示对应源文件的完整文件名

上述字符在映射到具体脚本中时将不会被引号自动包括起来，请在模板中用引号包括它们。

本工具链支持的批量压制采用如下脚本组合：为每个源文件创建一个 `.vpy` 文件做预处理，然后创建一个 `.py` 文件执行编码，比如：
```python
# template.vpy
import vapoursynth as vs
src = vs.core.lsmas.LWLibavSource(r"$src")
src.set_output()
```
```python
# template.py
import os
os.system(r'vspipe -c y4m "$bas.vpy" - | x265 --y4m --qpfile "$bas.qpfile" -o "$bas.hevc" -')
```
在***对应类文件夹下***创建好模板之后，运行
```python
rkt.map_config(path_to_vpy)  # 默认映射成 .vpy 文件
rkt.map_config(path_to_py, '.py')
```
将为模板所在目录下所有 `.m2ts` 后缀的源创建同名的 `.py` 和 `.vpy` 脚本。

若源后缀是 `.m2ts` 以外的文件，引入 `accept_ext` 修改，如想同时也给 `.mkv` 后缀的文件创建脚本：
```python
rkt.map_config(path_to_py, '.py', accept_ext=['.m2ts', '.mkv'])
# .vpy 文件同理
```

### 整理 qpfile
由于本工具链会为 30fps 的片源同时生成对应 24fps、30fps 和 60fps 的 qpfile（对应后缀分别为 `.24.qpfile`、`.30.qpfile` 和 `.60.qpfile`），对后续封装中对齐 PTS 有影响，因此若使用本工具链提供的封装工具，需将上述三种 qpfile 后缀选出一种并重命名为 `.qpfile`，比如要保留 30fps 对应的 qpfile：
```python
rkt.make_qpfile(path_to_class, '.30.qpfile')
```
如果出于某种原因，在运行 `make_qpfile` 前已经存在 `.qpfile` 文件，则其会被放在同文件夹下自动创键的 waste_qp 子文件夹内，如果想要强制改写该文件，可以引入参数 `force=True`。

## 批量压制
脚本映射完成后，通过 `rip` 函数批量执行 `.py` 文件：
```python
rkt.rip(path_to_rip)
```
函数自动对文件夹及所有子孙文件夹内后缀为 `.m2ts` 的源寻找同 basename 的 `.py` 文件并运行。如果想要增加源的种类，引入 `accept_ext` 参数，比如同时为后缀为 `.mkv` 的源批量压制：
```python
rkt.rip(path_to_rip, accept_ext=['.m2ts', '.mkv'])
```

# 手册
## link
函数原型：
```python
link(workspace_fp: str)
```
传入一个参数 `workspace_fp` 表示任意想要硬链接的文件夹路径，函数会生成 `workspace_fp + ‘_link’` 的硬链接副本。

如果 `workspace_fp + ‘_link’` 已存在，则在 `workspace_fp + ‘_link1’` 创建硬链接；若 `workspace_fp + ‘_link1’` 已存在，则在 `workspace_fp + ‘_link2’` 创建硬链接，以此类推。

## index
函数原型：
```python
index(workspace_fp: str, logger_fp: str = None, ffmpeg_fp: str = None, qponly: bool = False)
```
传入一个参数 `workspace_fp` 表示要处理的工作区路径，函数对工作区下的每一个 BD 子文件夹生成 qpfile 并检流、对检流出错和肉酱文件进行标记。

`logger_fp`：指定日志路径。如果不指定，函数会在工作区下记录日志文件 `index.年月日时分秒.log`。

`ffmpeg_fp`：指定 ffmpeg 路径。如果不指定，函数会在系统 Path 中找。

`qponly`：是否只生成 qpfile、不检流（也不会标记 vserr 文件）。

特别地，如果工作区只含一个 BD，你可以在整理时不为它单独建立一个文件夹，即路径可以是：
```text
WorkSpace
├─BDMV
│  ├─...
│  └─STREAM
├─...
```
运行本函数后，会自动创建一个文件夹将这个 BD 包装起来。

对于工作区下的多个 BD，每一个 BD 内的所有文件完成检流后会在 STREAM 文件夹下生成一个 `index.done` 文件标记，检测到该标记的 BD 不会重复检流。

检流错误的文件会生成一个 `.vserr` 标记，标记文件中会记录报错日志。

## collect
函数原型：
```python
collect(workspace_fp: str)
```
传入一个参数 `workspace_fp` 表示要整理的工作区路径。该函数将工作区中所有 BD 里没有 `.vserr` 标记的文件及其对应的 qpfile 硬连接到工作区下的 #Collection 文件夹中。如果 #Collection 已经存在，则会硬连接到 #Collection1 中；若 #Collection1 存在，则会硬连接到 #Collection2 中，以此类推。

## simple_sort
函数原型：
```python
simple_sort(tosort_fp: str, accept_ext: list = ['.m2ts']):
```
对 `tosort_fp` 指定的路径，搜索其所有子文件夹中所有后缀在 `accept_ext` 列表中的文件，将 `tosort_fp` 下文件名前缀能够匹配的文件归类到对应的子文件夹中。

## make_qpfile
函数原型：
```python
make_qpfile(dir: str, qp_ext: str = '.24.qpfile', force: bool = False):
```
将路径 `dir` 下的所有后缀为 `qp_ext` 的 qpfile 重命名成 `.qpfile`，若在运行 `make_qpfile` 前已经存在 `.qpfile` 文件，则其会被放在同文件夹下自动创键的 waste_qp 子文件夹内。若指定 `force=True`，则对已经存在的 `.qpfile` 强行改写。

## map_config
函数原型：
```python
def map_config(config_fp: str, config_ext = '.vpy', replace: bool = False, \
    accept_ext = ['.m2ts']):
```
对指定的模板，为每个指定后缀的源创建一份制定后缀的脚本文件。

`config_fp`：模板的路径。

`config_ext`：要映射的脚本后缀。

`replace`：是否要将已经存在的脚本强行改写成新模板（否则跳过）。

`accept_ext`：模板映射对应的源文件的后缀名。

## rip
函数原型：
```python
def rip(
    rip_path: str,
    recursion: bool = True, 
    vc_ext: str = '.hevc',
    run_ext: str = '.py', 
    accept_ext: list = ['.m2ts'],
    run_name: str = '__main__',
    logger_fp: str = None,
    num_redo: int = 1,
    multi_task: bool = False,
):
```
运行指定路径下的所有压制脚本。压制时将工作路径切换到源所在路径，使用 [run_path](https://docs.python.org/3/library/runpy.html#runpy.run_path) 执行脚本，支持多开模式和检查模式（默认）。压制开始时产生两种文件标记：`.busy` 和 `.break`。`.busy` 标记在脚本执行前创建，执行完成后删除，标记该视频流是正在被压制；在脚本执行完成后比较源的帧数和压制成品的帧数，如果帧数不同则创建 `.break` 标记，如果帧数相同则将现有 `.break` 标记移除。若对于一个源，存在指定后缀的视频流且不存在 `.break` 标记，则不再压制和检查帧数；若存在指定的视频流且存在 `.busy` 标记，在多开模式下将跳过该项压制，在检查模式下将重压。

`rip_path`：待压制的根目录路径。

`recursion`：是否对 `rip_path` 所有子孙文件夹都执行压制，否则忽略 `rip_path` 中的所有子文件夹。

`vc_ext`：压制成品文件的后缀。

`run_ext`：执行的 Python 脚本文件后缀（允许定制后缀如 `.30.py`），这个后缀是相对于源的 basename 而言的。

`accept_ext`：以列表的形式指定源文件的后缀类型。

`run_name`：参考 [runpy](https://docs.python.org/3/library/runpy.html#runpy.run_path) 的参数解释。

`logger_fp`：生成的日志的文件路径，如果不指定默认为 `rip_path` 下的 `rip.年月日时分秒.log`。

`num_redo`：重新检查的次数。第一轮压制完成后会逐一检查文件是否有 `.break` 标记，有则重压。

`multi_task`：`True` 开启多开模式，默认为 `False`，检查模式。