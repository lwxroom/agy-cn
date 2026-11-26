# agy-cn — Antigravity 轻量级安全中文启动器 (macOS)

一个极简、完全本地运行的 macOS 启动器，为 Google Antigravity 提供 **中英双语界面** 与 **本地自定义背景图**，不修改原版应用、不破坏签名、不开调试端口、不发起任何网络请求。

## 特性

- **零侵入、不破坏签名**：不解包 `app.asar`，不改动 `/Applications/Antigravity.app`，官方自动更新后依然可用。
- **管道模式，不开本地端口**：使用 Chromium `--remote-debugging-pipe` 私有匿名管道注入，不监听任何 TCP 端口，本机其他进程无法接入。
- **100% 本地离线**：零外部下载、零数据上报、零 `sudo`、零 Node.js 依赖（仅使用 macOS 自带 Python 3）。
- **中英双语对照**：菜单、按钮、标题等短标签默认显示 `中文 English`（如 `设置 Settings`），长句说明与动态时间/配额提示显示纯中文；自动跳过输入框、代码区与对话正文，避免误翻。
- **自定义背景图**：在 **「设置 Settings → 外观 Appearance」** 中内置「自定义背景图」卡片，支持本地选图、实时调节透明度与模糊度、切换「整个窗口 / 仅对话区」，配置仅保存于 `~/.agy-cn/bg-config.json`。
- **细节优化**：自动将设置侧栏的分组标题（`设置`、`项目`、`未归入项目`）弱化为不可点击的小号灰字，避免误触。

## 环境要求

- macOS
- 已安装 `/Applications/Antigravity.app`
- 系统自带 `python3`（无需额外依赖）

## 安装与使用

### 1. 克隆并安装

```bash
git clone https://github.com/lwxroom/agy-cn.git agy-cn
cd agy-cn
bash install.sh
```

安装脚本会将运行文件复制到 `~/.agy-cn/`，并在 `~/Applications/` 下生成 **「Antigravity 中文.app」**。

### 2. 启动中文版

1. 若原版 Antigravity 正在运行，先按 **`⌘Q`** 完全退出。
2. 在访达前往 `~/Applications/`，双击 **「Antigravity 中文」**（可拖到程序坞方便日后打开）。
   - 若 macOS 提示“无法验证开发者”，右键该图标 → 点「打开」即可。

### 3. 自定义背景图

打开左下角 **「设置 Settings」→「外观 Appearance」**，即可在 **「自定义背景图 Custom Background」** 卡片中上传本地图片并调节透明度、模糊度与显示范围。

### 4. 恢复英文 / 卸载

- **临时用回英文**：`⌘Q` 退出后，直接打开原版 `Antigravity.app` 即可。
- **彻底卸载**：
  ```bash
  bash uninstall.sh
  ```
  卸载仅删除 `~/.agy-cn/`、`~/Applications/Antigravity 中文.app` 及日志文件，原版应用与对话数据不受任何影响。

## 项目结构

| 文件 | 说明 |
|---|---|
| `launcher.py` | 启动器主程序：通过 `--remote-debugging-pipe` 管道启动 Antigravity 并注入界面层，负责本地保存背景图配置 |
| `overlay.js` | 运行时界面汉化层 + 双语标签 + 设置分组标题样式 + 外观页自定义背景图卡片 |
| `zh-CN.json` | 简体中文界面词典（可直接编辑增删词条） |
| `install.sh` | 安装脚本，生成 `~/Applications/Antigravity 中文.app` |
| `uninstall.sh` | 一键卸载脚本 |

## 已知限制

- macOS 原生顶部菜单栏（`File / Edit / View`）、原生右键菜单以及原生退出确认弹窗由系统框架渲染，不在网页视图内，因此保持英文不变。
- 对话标题由模型自动生成，属于用户内容而非界面词条，不通过词典翻译。

## 致谢与许可

- 本项目基于 [MIT License](LICENSE) 开源。
- `zh-CN.json` 中的基础界面词条衍生自 [guuguo/antigravity-zh-launcher](https://github.com/guuguo/antigravity-zh-launcher)（MIT License），在此表示感谢。
