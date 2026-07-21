### 国际化改造计划（先支持英文，支持实时切换，后续可扩展多语言）

#### Summary
- 目标是把“用户可见文本”从代码中彻底抽离，先完成 `zh_CN` / `en` 双语，并支持运行中即时切换（无需重启）。
- 改造将同时处理“显示文本”和“逻辑值耦合”问题：所有参与逻辑判断的中文枚举值改为稳定的英文代码（ASCII），UI 只显示翻译文本。
- 默认语言保持 `zh_CN`，英文品牌名使用常见英文写法（如 `Bilibili`, `Douyin`, `Kuaishou`）。

#### Implementation Changes
- 新增国际化基础层（建议放在 `ui/i18n/`）：
  - `LanguageManager(QObject)`：统一管理当前语言、加载语言包、`t(key, **kwargs)` 翻译、`language_changed` 信号。
  - 语言包资源：`locales/zh_CN.json`、`locales/en.json`，所有用户可见文案放入资源文件，不再在运行时代码硬编码中文。
  - 通用绑定工具：支持窗口标题、按钮文本、标签、占位符、Tooltip、消息框模板在 `retranslate_ui()` 中集中刷新。
- 统一“逻辑代码 vs 显示文本”：
  - 为所有下拉/单选等建立稳定 code（如 `crop_mode: pixel/center/percent`、`trim_mode: trim_edges/clip_range`、`status: pending/processing/done/failed/skipped/stopped`、`watermark_preset: bilibili_top_right` 等）。
  - `QComboBox` 使用 `userData=code`，采集配置与处理逻辑只读写 code，不再读写 `currentText()`。
  - 所有 `if xxx == "中文"` 分支改为 `if xxx == code`，并在 UI 层按语言映射展示。
- 语言设置与即时切换：
  - `OptionsConfigManager` 增加 `set_language()`，并复用现有 `get_language()`；语言持久化到 `options.ini [UI] Language`。
  - `OptionsDialog` 增加语言选择项，保存后发出语言变更；主窗口接收后调用 `LanguageManager.set_language()`。
  - 主窗口与关键弹窗（文本/水印/更多效果/预览相关窗口）实现 `retranslate_ui()`，已打开窗口在信号触发后即时刷新。
  - 动态创建的控件（如多水印配置行）在创建与语言切换时都执行文本重绑定。
- 处理链与状态文案改造：
  - `ui/batch_video/main_window.py` 与 `processor/batch_params_processor.py` 全面替换中文逻辑值、中文状态字串。
  - 进度、状态、汇总统计统一走 code，再由 UI 本地化展示；`ui/components.py` 的统计解析从中文键改为 code 键。
- 约束“禁止新增硬编码中文字段（用户可见）”：
  - 新增静态检查脚本（基于 AST/字符串字面量），扫描运行时代码中的用户可见字符串是否仍含中文。
  - 允许中文仅存在于语言包文件；注释/测试/文档不在本次强约束范围内。

#### Public API / Interface Changes
- 新增：
  - `LanguageManager.set_language(lang_code: str) -> None`
  - `LanguageManager.t(key: str, **kwargs) -> str`
  - `LanguageManager.language_changed` 信号
- 扩展：
  - `OptionsConfigManager.set_language(language: str)`
  - 选项保存数据增加 `ui_language`（或等价字段）传递给主窗口
- 内部接口变更（需全链路统一）：
  - UI 到处理器的配置字段由“中文文本值”改为“稳定 code 值”（如裁剪模式、方向、预设、状态等）

#### Test Plan
- 单元测试：
  - i18n 管理器：语言包加载、缺失 key 回退、格式化插值、语言切换信号。
  - 配置管理：`options.ini` 的语言读写与默认值（`zh_CN`）。
  - 处理器回归：以 code 值输入时，裁剪/文本/水印/更多效果逻辑结果与原行为一致。
- UI/集成测试：
  - 运行中切换 `zh_CN -> en -> zh_CN`，主窗口与已打开关键弹窗文本即时更新，无需重启。
  - 批处理状态流（处理中/完成/失败/跳过/停止）在两种语言下显示正确，统计弹窗正常。
- 静态检查：
  - 运行“硬编码中文检查”脚本，运行时代码不得残留用户可见中文字面量（语言包除外）。

#### Assumptions
- 范围按你确认：只覆盖用户可见文本，不强制改日志/注释/测试文档。
- 默认语言保持中文；英文作为可切换语言。
- 品牌名英文采用常见英文名称。
- 旧版本运行时内存态不做迁移；持久化仅保证 `options.ini` 语言项兼容。
