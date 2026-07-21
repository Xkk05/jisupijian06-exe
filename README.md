极速批剪
========

本项目为视频批量处理工具。
用于在本地环境下进行常见的视频批量任务操作。

版本更新命令
------------

- 补丁版本（Patch）：`python tools/bump_version.py patch`
- 次版本（Minor）：`python tools/bump_version.py minor`
- 主版本（Major）：`python tools/bump_version.py major`

打包命令
--------

- 直接打包（便携版 + 安装版）：`python build_release.py`
- 更新版本号并打包：`python build_release.py --set-version 1.0.1`
- 分阶段打包：
  - 仅构建便携版：`python build_release.py --phase portable`
  - 仅构建安装包 stage：`python build_release.py --phase stage`
  - 基于 stage 仅构建安装包：`python build_release.py --phase installer`
  - 基于 stage 仅构建更新包：`python build_release.py --phase update`
- 指定 Inno Setup 编译器路径（可选）：
  - PowerShell：`$env:INNO_SETUP_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"`

分布式签名打包（跨电脑）
------------------------

适用场景：本机负责编译，签名必须在另一台签名机完成，签完再回传继续打包。

### 一、推荐流程（你的场景）

1) 本机构建第一阶段待签文件（安装后目录中的全部可签名运行文件 + updater 源文件）：

```bash
python tools/distributed_sign_pipeline.py phase1-build
```

2) 将输出目录 `build/sign_jobs/<version>/phase1/pending/` 内文件复制到签名机工具输入目录签名，签完后把文件放回项目根目录：`signed_drop/phase1/`。

3) 在本机应用第一阶段签名结果（默认从 `signed_drop/phase1/` 读取）：

```bash
python tools/distributed_sign_pipeline.py phase1-apply
```

4) 构建安装包并导出第二阶段待签文件（安装包 exe）：

```bash
python tools/distributed_sign_pipeline.py phase2-build
```

5) 将 `build/sign_jobs/<version>/phase2/pending/` 送签并回传到：`signed_drop/phase2/`。

6) 在本机应用第二阶段签名结果（默认从 `signed_drop/phase2/` 读取）：

```bash
python tools/distributed_sign_pipeline.py phase2-apply
```

7) 最终生成更新包（zip + sha256）：

```bash
python tools/distributed_sign_pipeline.py finalize
```

### 二、状态与断点恢复

- 查看当前版本流程状态：`python tools/distributed_sign_pipeline.py status`
- 阶段命令默认幂等，已完成时会提示跳过。
- 需要强制重跑：
  - `phase1-build --force`
  - `phase2-build --force`
  - `phase1-apply --force`
  - `phase2-apply --force`

### 三、本地演练（无真实签名）

如果只是做链路验证，可将 pending 文件原样复制到 `signed_drop/phase1` 或 `signed_drop/phase2`，并在 apply 命令加：

```bash
--allow-unsigned-signed-input
```

例如：

```bash
python tools/distributed_sign_pipeline.py phase1-apply --allow-unsigned-signed-input
```

### 四、常见问题

- 回传目录缺文件：脚本会报错并列出缺失文件名。
- 回传目录有多余文件：脚本会报错并列出多余文件名，防止串版本。
- 检测到未签名：默认报错；仅演练时使用 `--allow-unsigned-signed-input`。
- 如需自定义回传目录，仍可使用：`--signed-dir "你的目录"`
- 若你之前已经执行过旧版 `phase1-build`（只导出 2 个文件），请执行：`python tools/distributed_sign_pipeline.py phase1-build --force`
