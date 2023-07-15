# rkstool
***The framework was originally constructed by mein Führer Alice.***

**Special Thanks to Jan, x_x.**

## 设计构想
首先，为了辅种方便和误操作后能够重开，需要对整个原种做硬链接；***提示：你不能在 FAT 格式的分区上做硬链接，推荐在 NTFS 分区上完成工作。***

原盘硬链接的结果是可以随意剪切粘贴重命名的，出于方便，需要手动整理原盘文件结构，整理好后可被称为一个“工作区”（WorkSpace），后文会给出一个工作区的例子，简单来说工作区下需陈列一系列对齐的原盘，每个原盘对应一个子文件夹，子文件夹下面有 `BDMV`、该 `BDMV` 下有 `STREAM`，即删去中间所有不必要的单层嵌套。*特别地，对于一些只含一个原盘的种子，允许整理的时候直接把 `BDMV` 及其同级文件夹暴露在工作区下，工具链自动把工作区下的这些裸露原盘打包*。对每个原盘，计算出所有的 `qpfile`。对每个原盘内的每个文件，解码其视频流，筛选出无需压制的视频文件和由于种种原因无法完整解码的视频文件并标记。

上一步完成后，工具链将所有原盘的未被标记的视频文件及其对应的 `qpfile`（如果有的话）抽出，硬链接到工作区下与所有原盘平级的一个 `#Collection` 文件夹内，并重命名成 `原盘名_文件名` 的格式。

上一步完成后，对于 `#Collection` 文件夹，直到抽混流步骤之前，工具链对 BD 和普通压制任务（如 WEB）一视同仁。

接下来要做的是分类，分类的原则是处理相似的放在一个子文件夹内、内容相似的放在一个子文件夹内。具体的实现方法是手动新建一系列子文件夹，将视频文件（工具链可以指定可识别的后缀）分类放入后，工具链再将其对应的（文件名前缀相同的）辅助文件一并塞入对应的文件夹。***对于工具链工作在的那个文件夹来说，你只能先完成一层的子文件夹分类，在子文件夹里创建子文件夹是识别不了的。***

分类完成后就可以执行压制了，批量化压制的整体构想是：有一个 `.vpy` 文件，实现对某视频文件的处理；又有一个 `.py` 文件，具体执行压制命令；即最后批量运行的时候只需运行所有合法的 `.py` 文件即可。由于之前已经对视频文件进行了分类，分类好的子文件夹里的所有视频文件可以被认为是能用同一预处理送压的，因此工具链还需具备将某一组 `.vpy` 和 `.py` 模板映射给某文件夹内的所有视频文件的功能。

映射部分吸取了前工具链的经验，将 `.vpy` 和 `.py` 分别映射，并可以指定是否强制覆盖。映射源只需是文本文件，后缀无所谓。提供两个映射符号：文本中的 `$src` 对应要映射的文件名（比如“BD1_00000.m2ts”）、`$bas` 对应要映射的文件名前缀（比如“BD1_00000”）。

压制部分，考虑到一些人的多开压制需求，同时支持多开模式和检查模式：一个视频文件在压制时会产生一个 `.busy` 标记，多开模式下碰到该标记自动跳过，检查模式下碰到该标记则覆盖重压。每个视频压完后，利用 vapoursynth 检查压制后的视频与源是否帧数相同，不同则被认为断压，产生一个 `.break` 标记。工具链提供一个“重压次数”参数，允许在次数范围内检查标记并重压。

对于 BDRip 来说，压制完成后就可以进行抽混流了。由于一些原因，我用 [tsmuxer](https://github.com/justdan96/tsMuxer) 获取流信息、用 [eac3to](https://forum.doom9.org/showthread.php?t=125966) 实际执行抽取。由于有些制作商会在各种情况下复制凑数音轨，抽取完成后需要检查并将冗余音轨抛弃，这里使用 [librosa](https://librosa.org/) 库实现检查。抽流完成后，利用 `qpfile`` 和视频文件产生 PTS 对齐后的章节。最后使用 [mkvmerge](https://mkvtoolnix.download/) 封装。

# Original Toolchain GUIDELINE
## 1. "ks_0link&更改权限.exe"
第一步是通过硬链接（因此请在 `NTFS` 格式硬盘上完成所有工作）创建 `BDMV` 源副本，在此之前你需要整理一下 `BDMV`，类似这样：
```text
Vol.2-4_WorkSpace/
└── Vol.2-4
    ├── HORIMIYA_2
    │   ├── BDMV
    │   │   ├── ...
    │   │   └── STREAM
    │   └── ...
    ├── HORIMIYA_3
    │   ├── BDMV
    │   │   ├── ...
    │   │   └── STREAM
    │   └── ...
    └── HORIMIYA_4
        ├── BDMV
        │   ├── ...
        │   └── STREAM
        └── ...
```
目录名怎样并不重要，反正最后都要重命名，自己能看懂就行了。

接下来将 `Vol.2-4` 文件夹拖到 `ks_0link&更改权限.exe` 上，很快，`Vol.2-4_WorkSpace` 下出现了一个 `Link` 文件夹：
```text
Vol.2-4_WorkSpace/
├── Link_Vol.2-4
│   ├── HORIMIYA_2
│   │   ├── BDMV
│   │   │   ├── ...
│   │   │   └── STREAM
│   │   └── ...
│   └── ...
└── Vol.2-4
    └── ...
```
内容看起来应该完全一样，我建议检查一下 `STREAM` 里面的 `m2ts` 数量是否正确。

## 2. "ks_1index_api4.exe"
下一步是索引所有的流，将 `ks_1index_api4.exe` 放到 `Link_Vol.2-4/` 目录下双击。不出意外它应该运行较长时间，如果你想减少不必要的工程量也可以把不用做的 `STREAM` 删掉（比如如果你已经压过某些文件不需要再处理它们了）。

做完之后，你应该能看到每个能播放的 `m2ts` 旁边多了三个文件，一个是索引 `lwi`，一个是章节 `chapter`，还有一个帧率 `def` 文件。

## 3. "ks_2pre.exe"
接下来我们整理文件，把流和章节提取出来。将 `ks_2pre.exe` 放到 `Link_Vol.2-4/` 目录下双击。很快，`Link_Vol.2-4/` 下出现了一个名为 `#ks` 的文件夹：
```text
./Vol.2-4_WorkSpace/Link_Vol.2-4/
├── #ks
│   ├── 24_HORIMIYA_2_00000.ks45.txt
│   ├── 24_HORIMIYA_2_00000.m2ts
│   ├── 24_HORIMIYA_2_00000.m2ts.lwi
│   ├── ...
│   ├── 24_HORIMIYA_3_00000.ks45.txt
│   ├── 24_HORIMIYA_3_00000.m2ts
│   ├── 24_HORIMIYA_3_00000.m2ts.lwi
│   ├── ...
│   ├── 24_HORIMIYA_4_00000.ks45.txt
│   ├── 24_HORIMIYA_4_00000.m2ts
│   ├── 24_HORIMIYA_4_00000.m2ts.lwi
│   └── ...
├── HORIMIYA_2
│   └── ...
├── HORIMIYA_3
│   └── ...
├── HORIMIYA_4
│   └── ...
├── ks_1index_api4.exe
└── ks_2pre.exe
```
命名不难理解。

## 4. "ks_3sort.exe"
这是一个分类工具，双击打开，你能看见一个长输入框、一个短输入框和下面大片的空白。

这个工具最基本的用法是，在资源管理器中多选同类型的 `m2ts`（比如他们都是 `PV`）拖入空白区域，在长输入框中输入类名，然后按下 `Ctrl+Q` 执行，在资源管理器中你不难看到所有相关文件都被丢进类子文件夹中了。

如果你不想处理某个文件，你可以不把它分类，留在文件夹中也行、直接删掉也行，只要它的旁边没有由后文所述生成的脚本，它就不会被送压和封装。

下面是一个整理（删除不必要文件）后的版本：
```text
./Vol.2-4_WorkSpace/Link_Vol.2-4/#ks/
├── Menu
│   ├── 24_HORIMIYA_2_00013.ks45.txt
│   ├── 24_HORIMIYA_2_00013.m2ts
│   ├── 24_HORIMIYA_2_00013.m2ts.lwi
│   └── ...
├── OP Ver.2
│   ├── 24_HORIMIYA_4_00002.ks45.txt
│   ├── 24_HORIMIYA_4_00002.m2ts
│   └── 24_HORIMIYA_4_00002.m2ts.lwi
├── Preview
│   ├── 24_HORIMIYA_2_00002.ks45.txt
│   ├── 24_HORIMIYA_2_00002.m2ts
│   ├── 24_HORIMIYA_2_00002.m2ts.lwi
│   └── ...
└── TV
    ├── 24_HORIMIYA_2_00000.ks45.txt
    ├── 24_HORIMIYA_2_00000.m2ts
    ├── 24_HORIMIYA_2_00000.m2ts.lwi
    └── ...
```

## 5. "ks_4map.exe"
接下来我们写批处理脚本，它是一个 `.ini` 文件，一个简单的例子见 `BD_Sample.ini`。

两个分号后的是注释。你需要为不同帧率创建不同的脚本，如果要处理的源中没有 30FPS 的，你可以不写它。处理同一类型的源需要两个脚本，其中一个是 `VapourSynth` 脚本，另一个是 `Python` 脚本，前者不必解释，后者的作用基本就是给出 `x265` 命令。

如 `BD_Sample.ini` 中所示，写 `VapourSynth` 脚本时你可以用 `$src` 表示源文件的文件名，写 `Python` 脚本时可以用 `$bas` 表示生成 `.vpy` 文件名的前缀，`.vpy` 文件名的全称受到定义的影响，如 `24.m2ts/24.vpy` 将生成 `$bas.24.vpy`，这一点应该不难理解。

`os.environ['Path']` 开头的一句表示设置系统路径，其后两个 `os.system(...)` 分别起到处理索引文件和创建 `qpfile` 的作用，他们依赖 `m2tslwi.exe` 和 `mkqpfile45.exe`，这是 `x26x` 中的可执行文件，他们已经被加入到 `os.environ['Path']` 中。

当你编写好一个 `.ini` 配置文件（比如 `Bilateral.ini`）时，把它放在上一步分好的某个类子文件夹下，比如 `Menu`，接着将它拖到 `ks_4map.exe` 上运行，它将为每个合法的 `m2ts` 创建两个对应的脚本：
```text
./Vol.2-4_WorkSpace/Link_Vol.2-4/#ks/Menu/
├── 24_HORIMIYA_2_00013.24.vpy
├── 24_HORIMIYA_2_00013.ks45.txt
├── 24_HORIMIYA_2_00013.m2ts
├── 24_HORIMIYA_2_00013.m2ts.lwi
├── 24_HORIMIYA_2_00013.py
├── 24_HORIMIYA_3_00013.24.vpy
├── 24_HORIMIYA_3_00013.ks45.txt
├── 24_HORIMIYA_3_00013.m2ts
├── 24_HORIMIYA_3_00013.m2ts.lwi
├── 24_HORIMIYA_3_00013.py
├── 24_HORIMIYA_4_00013.24.vpy
├── 24_HORIMIYA_4_00013.ks45.txt
├── 24_HORIMIYA_4_00013.m2ts
├── 24_HORIMIYA_4_00013.m2ts.lwi
├── 24_HORIMIYA_4_00013.py
└── Bilateral.ini
```

你可以双击 `.vpy` 预览，也可以在此基础上进行修改。

编写 `x265` 参数的过程中，你需要注意必须引入 `--min-keyint 1 --no-open-gop` 参数，除非他们已经被默认包含。另外，`BD_Sample.ini` 里写的是 `x265_10`，如果你和我情况相同显然就要改成 `x265-10b`。

### 针对脚本使用者的特殊说明

现存脚本包括 API3 和 API4 两种，无论如何你都应该尽量使用 API4，API4 由于工具链当前版本本身的原因，暂不支持使用 API4 版本的 VapourSynth 来进行一些内部操作，要让 API4 的脚本能够正常使用，目前的办法是在配置文件中手动指定 `VSPipe.exe` 的位置为 API4 版本的 `VSPipe.exe` 的位置，详情请参考 MapFilter 仓库的[说明](https://github.com/AliceTeaParty/MapFilter#%E5%85%B3%E4%BA%8E-api4-%E7%89%88%E6%9C%AC%E7%9A%84%E7%89%B9%E6%AE%8A%E8%AF%B4%E6%98%8E)。

## 6. "ks_5rip_api4.exe" & "ks_5rip_264_api4.exe"
这个可执行文件自动完成压制工作，其作用域逻辑可以参见前述章节，推荐把它放在目录下双击，比如想只压制 `Menu/` 的内容，你就把它放在 `Menu/` 下，或者如果你想压制所有内容，就放在 `#ks/` 下。

`ks_5rip_264_api4.exe` 支持使用 x264 编码器时输出 `.264` 后缀的文件，但也因此忽略了一些检查，压制 hevc 时建议还是使用 `ks_5rip_api4.exe`。

## 7. "ks_6mkv_flac_success_sound_off_api4.exe"

接下来需要进行抽轨、封装、提取章节、对齐 `pts`、再次封装的一系列流程，对齐 `pts` 主要是为了方便切割。显然你不能删掉 `m2ts` 文件和 `qpfile` 文件，没了前者你就不能提取音轨和字幕轨，没了后者你就不能对齐 `pts` 了。一般情况下你把它放在 `#ks/` 下双击运行即可，它会检查现有的封装并合理跳过。

需要注意的是，这个可执行文件会删掉距离视频边缘两秒以内的章节，如果你想要保留开头的章节，你可以在下一步中使用 `ForceAddChapter.exe` 代替 `ks_7mkv2flac_aac.exe`，它会在视频开头添加一个章节。

## 8. "ks_7mkv2flac_aac_sup.exe"

这是个程序它负责将第二条及以后的音轨转成 `AAC` 有损编码。你实际上可以选择任意一条音轨，使其保留成无损（但只有它一个可以），要想实现这件事只需在运行本程序之前交换音轨顺序，把你想要保留成无损的音轨调到第一个即可。一般情况下你把它放在 `#ks/` 下双击运行就好。
