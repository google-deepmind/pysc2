<div align="center">
  <a href="https://www.youtube.com/watch?v=-fKUyT14G-8"
     target="_blank">
    <img src="http://img.youtube.com/vi/-fKUyT14G-8/0.jpg"
         alt="DeepMind open source PySC2 toolset for Starcraft II"
         width="240" height="180" border="10" />
  </a>
  <a href="https://www.youtube.com/watch?v=6L448yg0Sm0"
     target="_blank">
    <img src="http://img.youtube.com/vi/6L448yg0Sm0/0.jpg"
         alt="StarCraft II 'mini games' for AI research"
         width="240" height="180" border="10" />
  </a>
  <a href="https://www.youtube.com/watch?v=WEOzide5XFc"
     target="_blank">
    <img src="http://img.youtube.com/vi/WEOzide5XFc/0.jpg"
         alt="Trained and untrained agents play StarCraft II 'mini-game'"
         width="240" height="180" border="10" />
  </a>
</div>

# PySC2 - 星际争霸 II 强化学习环境 (StarCraft II Learning Environment)

<p align="center">
  <a href="README.md">English</a> · <b>简体中文</b>
</p>

[PySC2](https://github.com/deepmind/pysc2) 是 [DeepMind](http://deepmind.com) 为星际争霸 II 学习环境（SC2LE，StarCraft II Learning Environment）开发的 Python 组件。它将[暴雪娱乐（Blizzard Entertainment）](http://blizzard.com)的[星际争霸 II 机器学习 API](https://github.com/Blizzard/s2client-proto) 封装并公开为 Python 强化学习（RL）环境。这是 DeepMind 与暴雪联合开展的一项合作，旨在将《星际争霸 II》打造为一个功能丰富的强化学习研究环境。PySC2 为 RL 智能体（Agent）提供了与《星际争霸 II》交互的标准化接口，包括获取环境观测（Observation）以及发送操作动作（Action）。


我们发布了配套的[官方博客文章](https://deepmind.com/blog/deepmind-and-blizzard-open-starcraft-ii-ai-research-environment/)与[学术论文](https://arxiv.org/abs/1708.04782)，概述了我们使用《星际争霸 II》开展深度强化学习（DeepRL）研究的初衷，以及基于该环境取得的初步研究成果。

## 关于 (About)

免责声明：本软件非 Google 官方正式产品。

若在您的学术研究中使用了星际争霸 II 机器学习 API 和/或 PySC2，请引用[星际争霸 II 论文 (StarCraft II Paper)](https://arxiv.org/abs/1708.04782)。

您可以通过 [pysc2@deepmind.com](mailto:pysc2@deepmind.com) 联系我们。


# 快速入门指南 (Quick Start Guide)

## 获取 PySC2 (Get PySC2)

### 通过 PyPI 安装

获取 PySC2 最便捷的方式是使用 pip：

```shell
$ pip install pysc2
```

该命令将安装 `pysc2` 依赖包及所有必需的依赖项。[virtualenv](https://pypi.python.org/pypi/virtualenv) 可用于管理您的依赖环境。若安装遇到问题，可能需要先升级 pip：`pip install --upgrade pip`。若在较旧的系统上运行，可能需要安装适用于 `pygame` 依赖的 `libsdl` 相关库。

Pip 会将部分可执行二进制脚本安装到您的系统的 bin 目录中。例如 `pysc2_play` 可作为运行 `python -m pysc2.bin.play` 的快捷命令。

### 从源码安装 (From Source)

或者，您也可以直接从 git master 分支安装最新的 PySC2 代码：

```shell
$ pip install --upgrade https://github.com/deepmind/pysc2/archive/master.zip
```

或通过本地克隆的 git 仓库进行安装：

```shell
$ git clone https://github.com/deepmind/pysc2.git
$ pip install --upgrade pysc2/
```

## 获取《星际争霸 II》客户端 (Get StarCraft II)

PySC2 依赖完整的《星际争霸 II》游戏客户端，且仅支持包含 API 接口的 3.16.1 及以上版本。

### Linux

请遵循暴雪的[官方文档](https://github.com/Blizzard/s2client-proto#downloads)获取 Linux 版本客户端。默认情况下，PySC2 假定游戏安装在 `~/StarCraftII/` 目录下。您可以通过设置环境变量 `SC2PATH` 或创建自定义 run_config 来覆盖此路径。

### Windows / macOS

直接从 [战网（Battle.net）](https://battle.net) 正常下载安装游戏客户端即可。即使是[免费的入门版本（Starter Edition）](http://battle.net/sc2/en/legacy-of-the-void/)也能正常支持。若您使用的是默认安装路径，PySC2 应能自动定位最新的游戏可执行程序。如果您自定义了安装目录，则可能需要将环境变量 `SC2PATH` 设置为对应的正确路径。

PySC2 支持在运行 Python 3.8+ 的 macOS 和 Windows 系统上运行，但主要在 Linux 环境下经过了全面深入的测试。我们非常欢迎有助于提升与其他操作系统兼容性的建议与补丁。

## 获取游戏地图 (Get the maps)

PySC2 预配置了多种地图，但在运行前必须先将它们下载解压到 SC2 的 `Maps` 目录下。

请下载[天梯地图（ladder maps）](https://github.com/Blizzard/s2client-proto#downloads)以及[迷你游戏地图（mini games）](https://github.com/deepmind/pysc2/releases/download/v1.2/mini_games.zip)，并将它们解压至您的 `StarCraftII/Maps/` 目录中。

## 运行智能体 (Run an agent)

您可以运行一个智能体来测试环境是否正常工作。图形界面会直观展示智能体的操作动作，非常便于调试与可视化分析：

```shell
$ python -m pysc2.bin.agent --map Simple64
```

默认会运行一个随机动作智能体，但您可以指定其他智能体，包括自定义的智能体实现：

```shell
$ python -m pysc2.bin.agent --map CollectMineralShards --agent pysc2.agents.scripted_agent.CollectMineralShards
```

您还可以让两个智能体相互对抗：

```shell
$ python -m pysc2.bin.agent --map Simple64 --agent2 pysc2.agents.random_agent.RandomAgent
```

如需指定智能体的种族、对手难度等级等参数，可以传入相应的命令行标志。运行 `--help` 即可查看所有可配置项。

## 以人类玩家身份进行游戏 (Play the game as a human)

系统提供了一个人类智能体界面，主要用于调试，但也可以用来亲自游玩。该界面相对简明直接，但足以用来理解游戏的基本要素，并且支持在 Linux 下运行：

```shell
$ python -m pysc2.bin.play --map Simple64
```

在界面中按下 `?` 键可查看快捷键列表。最基础的快捷键包括：`F4` 退出、`F5` 重新开始、`F8` 保存录像对局，以及 `Pgup`/`Pgdn` 调节游戏速度。操作时使用鼠标进行框选，使用键盘执行左侧列出的控制指令。

左侧为基础渲染视图，右侧为智能体接收到的特征层（Feature layers），并添加了色彩编码以便于人类直观阅读。您可以通过命令行标志开启或禁用 RGB 画面或特征层渲染，并自定义其分辨率。

## 观看游戏录像对局 (Watch a replay)

运行智能体或人类游玩默认都会保存游戏录像。您可以通过以下命令回放录像：

```shell
$ python -m pysc2.bin.play --replay <path-to-replay>
```

只要游戏能够找到对应的地图文件，该命令适用于任何录像文件。

控制方式与实际游戏一致，例如按 `F4` 退出、按 `pgup`/`pgdn` 调节播放速度等。

您还可以通过添加 `--video` 标志将录像渲染保存为视频文件。

## 列出可用地图 (List the maps)

[地图配置](docs/maps.md)需要预先登记才能被环境识别。运行以下命令即可查看所有已知地图的列表：

```shell
$ python -m pysc2.bin.map_list
```

## 运行测试套件 (Run the tests)

若您计划提交 Pull Request，请确保相关测试能够正常通过：

```shell
$ python -m pysc2.bin.run_tests
```

# 环境详细说明 (Environment Details)

有关环境具体如何配置、观测空间与动作空间如何运作的完整技术细节，请参阅[环境文档](docs/environment.md)。

请注意，现已推出该环境的替代版本，该版本使用为 AlphaStar 开发的 C++ 包装器提供了更加丰富的动作与观测格式。详情请参阅[转换器文档](docs/converters.md)。

# 迷你游戏地图 (Mini-game maps)

论文中引用的迷你游戏地图文件存放在 `pysc2/maps/` 目录下，但必须安装到 `$SC2PATH/Maps` 中。请务必遵循上文的下载指引。

地图配置定义在 `pysc2/maps/` 下的 Python 文件中。这些配置可以设置玩家数量、时间限制、使用游戏输赢结果还是课程评分（curriculum score）等诸多参数。欲了解有关地图的更多信息以及如何自定义专属地图，请参阅[地图文档](docs/maps.md)。

# 游戏录像对局数据 (Replays)

游戏录像让您能够回顾一场对局中发生的所有事件，查看每位玩家在对局过程中产生的所有动作与观测。

暴雪公开了大量天梯对局的匿名 1v1 录像数据。您可以在其官网上找到如何获取[录像文件](https://github.com/Blizzard/s2client-proto#downloads)的说明。您也可以分析复盘自己打出的录像。

录像文件可以通过回放重新提取该对局中的观测与动作数据。观测画面会按照您请求的分辨率进行渲染，因此可能与人类玩家当时实际看到的画面存在差异。同理，动作指定的是具体坐标点，在人类屏幕上可能对应不同像素，因此在我们的观测中未必能做到完全绝对像素对齐，但两者在语义上高度近似。

录像是版本敏感的，例如 3.16 版本的录像在 3.16.1 或 3.17 的客户端程序中将无法正常回放。

您可以使用完整游戏客户端或通过 `pysc2.bin.play` 可视化回放录像。或者，您也可以运行 `pysc2.bin.replay_actions` 并行批量处理大量录像数据。

---

> **翻译说明（Translation Disclaimer）**
> 本文档由社区志愿者（[@JasonYeYuhe](https://github.com/JasonYeYuhe)）人工翻译并维护，旨在降低中文开发者的阅读门槛。最后同步日期：2026年10月18日。若译文与英文原版存在任何出入或滞后，请以 [英文原版 (README.md)](README.md) 为准。欢迎通过 PR 协助改进译文！
