# Public repository preparation — 2026-11-10

- Environment: macOS, CPython 3.11, project virtual environment.
- Current suite: **52 passed** (`python -m pytest -q`, 11.35 seconds).
- Five real Qt screenshots generated offscreen using synthetic documentation data; the example revision is manually authored, not an LLM benchmark.
- Documentation updated for current default statistics-only training, Fast/Detailed sampled learning, cache reuse, model settings dialog, and the Python 3.11 recovery dependency.
- Publication excludes local corpora, manuscripts, preferences, environments, IDE files, and unrelated parent-repository history.
- GUI implementation still depends on bundled `gui_recovery.pyc`; full GUI source restoration remains outstanding.
- This run did not download models, install Ollama, or revalidate external OpenAlex/Ollama services. Earlier observations below are historical.

---

# 0.2.0 验证记录

验证日期：2026-11-10。新增三语工具栏、Light / Dark / System 外观、双向同步的模型选择、模型准备 / 测试 / 安装更新，以及草稿修改前的自动模型准备。

- **30 项测试通过**：原有文档与模型档案测试，加上三语切换保留草稿、完整界面文案覆盖、偏好持久化且不存 API key、暗色 / 亮色输入框颜色、System 外观变化、模型选择同步、自定义已安装模型、选中模型和说明语言传入第三步、缺失模型下载、缺失运行环境安装分支、取消、自定义端口保护、下载未完成判断、运行环境版本验证和不支持系统的安装保护。
- **真实本机检查**：成功读取 `qwen2.5:7b` / `qwen2.5vl:7b` 清单；准备已安装的 `qwen2.5:7b` 时未重新下载；短文本响应测试返回 `OK`。
- **界面检查**：查看德语深色设置页、英语亮色草稿页、中文深色训练页截图，确认控件和内容区主题一致。System 模式的系统颜色变化使用可控测试验证。
- **安装验证范围**：安装 / 更新的控制流程和保护分支使用模拟测试；未实际重装本机现有 Ollama，也未进行 Windows 实机安装。缺失模型的下载使用模拟响应验证，避免测试过程中下载额外的大模型。
- **语言范围**：翻译界面和应用提示，新修改说明按界面语言生成；论文正文、作者姓名、论文标题、既有生成内容和外部服务原始诊断不自动翻译。

# 0.1.0 验证记录

验证日期：2026-11-10。环境：macOS、Python 3.10 独立虚拟环境。

- 自动化：17 项测试通过。覆盖 DOCX 正文与表格顺序、文本去重、无损分块、冻结档案更新与失败保护、训练取消、修改恢复记录、数值 / 引用 / 谨慎措辞检查、参考文本重叠、HTML 转义、Word 导出、下载大小限制、非 PDF 响应、公网地址检查、API 分页、截断模型响应，以及 GUI 编辑状态保存。
- GUI：离屏启动四个工作区，并人工检查文献训练页与草稿对比页的窗口截图。
- 实际 OpenAlex：作者搜索返回 4 条候选；指定作者后成功返回 2 篇论文元数据。公开全文下载通过模拟流式响应验证，未对大规模出版社下载进行压力测试。
- 实际 Ollama：使用本机已安装的 `qwen2.5:7b`，在临时目录导入合成示例 DOCX，成功生成 16 条风格规则，完成单段草稿修改并保存恢复记录。测试没有使用用户未提供的论文或草稿。
- 实际模型暴露的问题：仅使用 JSON 模式不能稳定返回目标字段，已经改用 JSON Schema 结构约束，随后端到端测试成功。
- 输出质量限制：实测修改稿曾增加原草稿未包含的谨慎解释，并靠近参考语句。长度与谨慎措辞检查触发；随后加入连续 8 个英文单词的参考重复检查，并强化不引入参考论文结论的提示词。该检测有独立回归测试；不代表语义正确性已被证明。

尚未验证：接近 512 MB 文件的压力处理、多种扫描 / 多栏 PDF、全部 Ollama 模型、Windows 实机和真实导师语料的风格匹配效果。应用内明确要求人工审阅；这是可运行的第一版，不是自动保证科学准确性的编辑器。
