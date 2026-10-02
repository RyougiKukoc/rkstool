# rkstool
***The framework was originally constructed by mein Führer Alice.***

**Special Thanks to Jan, x_x.**

# Installation

Requires Python 3.10 or newer.
```
pip install --force-reinstall git+https://github.com/RyougiKukoc/rkstool.git
```

# Documents

See [Wiki](https://github.com/RyougiKukoc/rkstool/wiki).

# Runtime requirements

Runtime dependencies remain intentionally undeclared in `pyproject.toml`.
Install the Python modules needed by your scripts yourself; normal imports
report missing modules. Functions that call mkvmerge, ffmpeg, ffprobe, eac3to,
tsmuxer or qaac also need those external tools. A pure Python wheel does not
bundle these programs or promise that every function works on every OS.

# Manual wheel synchronization

This repository remains the source of truth for the module and its version.
After updating the source and `project.version`, manually run **Sync wheel
preview** in Actions and select the source ref. The notifier resolves a fixed
commit and asks the [central wheels repository](https://github.com/AliceTeaParty/vapoursynth-api4-wheels)
to build it under `modules/rkstool/`. This creates a preview artifact; a central
maintainer separately performs the manual publication of the validated wheel.

Configure the repository secret `WHEELS_UPDATE_TOKEN` with a credential limited
to Actions write on the central wheels repository. The repository's default
`GITHUB_TOKEN` cannot trigger the central build. Without that secret, run the
preview directly in the central repository or submit a version request PR
through its [module interface](https://github.com/AliceTeaParty/vapoursynth-api4-wheels/tree/main/modules).

After an explicit central publication:

```shell
python -m pip install --extra-index-url https://aliceteaparty.github.io/vapoursynth-api4-wheels/simple/ rkstool
```
