# 怪p法律尽职调查

**公开版 1.75**

把法律尽调的委托范围、工作说明或要点表，转成编号资料目录；审阅已收材料、提出补件要求；起草或复核法律尽职调查报告。

适用于公司、上市或并购法律尽调，尤其是日本公司及中日跨境项目。也可以只用其中一环——单独核对范围、资料清单、报告、批注或交付格式。

> **免责声明**：本技能提供工作方法与文本模板，不构成法律意见，使用时不建立律师—客户关系；具体项目的范围、适用法与结论，应由执业律师依当地规则独立判断。

## 安装

| 使用方式 | 做法 |
| --- | --- |
| DeepSeek Harness | 把整个文件夹复制到 `~/.dsh/skills/`（Windows 为 `C:\Users\<你>\.dsh\skills\`），或项目的 `.dsh/skills/` |
| Claude Code 等支持 Agent Skills 的工具 | 复制到该工具的技能目录；也可用 `npx skills add <你的用户名>/<仓库名>`，或直接下载本仓库放进技能目录 |
| 其他 AI | 在获准使用的环境中提供所需文件及 [SKILL.md](SKILL.md)，请它按该工作流处理 |

安装后不需要额外依赖。只有范围核对脚本需要 Python 3.10 或更高版本，仅用标准库，可离线运行。

## 目录结构

```
SKILL.md                    工作流入口：四阶段、每阶段的产物与判断规则
references/                 方法与样稿
  sample-scope.md             虚构专项案例的七项核查范围
  evidence.md                 资料目录编号、内部对应表、法条核验底稿、批注标签
  conclusions.md              从审阅材料到结论的五种写法与实例
  drafting-style.md           定稿表述对照（"未发现"与"公司确认"的区别等）
  report.md                   报告结构、版式、批注与交付
  example.md                  虚构示例：编号与批注怎么落地
  sample-focused-report.md    虚构专项报告全文
  sample-listing-report.md    上市专项尽调报告目录与节选
  alternative-report-outlines.md  通用报告框架
  sample-request-list.csv     资料目录纯文本版
  sample-report-map.csv       要点与报告位置的对应表
assets/
  sample-focused-report.docx  专项报告 Word 示例
  report-template.docx       空白 Word 模板
  sample-request-list.xlsx    Excel 填写示例与空白清单
  icon.svg                    图标
scripts/check_scope.py        核对要点覆盖、占位符与批注的离线脚本
tests/                        单元测试与四道复核题
agents/openai.yaml            部分平台读取的显示信息
```

## 从哪开始

| 手头的工作 | 先看 |
| --- | --- |
| 按工作范围编资料目录 | [要点表](references/sample-scope.md)和[资料目录 Excel](assets/sample-request-list.xlsx)（[CSV](references/sample-request-list.csv)） |
| 核对收件、判断由谁补件 | [资料目录与证据台账](references/evidence.md)和[编号示例](references/example.md) |
| 起草或复核专项尽调报告 | [专项尽调报告 Word](assets/sample-focused-report.docx)及[报告 Markdown](references/sample-focused-report.md) |
| 收到补件或准备出具报告 | [结论写法示例](references/conclusions.md) |
| 起草上市尽调报告 | [上市专项虚构示例](references/sample-listing-report.md) |
| 复核报告语言 | [定稿表述对照](references/drafting-style.md) |
| 检查报告分章和交付格式 | [报告结构与交付](references/report.md)和[可选报告框架](references/alternative-report-outlines.md) |

专项尽调的要点表、资料目录和报告使用配套编号。完整版包括空白 Word 模板及 Excel 空白页。案例和数据均为虚构；实际工作时按本项目修改范围、表头、编号和核查期间。

可以直接对 AI 说："请按 SKILL.md 处理附件。先根据委托范围编资料目录，按主题编号，并在最右列列出对应条项。已有材料请先核对。需要公司确认或补件的，请写明具体事项和原要点条项。"

## 核对范围与报告位置

在仓库目录运行以下命令。需要 Python 3.10 或更高版本，可离线使用。

```sh
python scripts/check_scope.py --scope references/sample-scope.md --section "核查事项" --mapping references/sample-report-map.csv --report references/sample-focused-report.md --final
```

本例使用虚构案例，核对七项核查事项。在完整版中，也可将报告路径替换为 `assets/sample-focused-report.docx`。

新项目替换三个输入文件。范围可用 Markdown 中指定标题下的顶层阿拉伯数字编号清单。其他编号或多部分重号时，从已确认的要点表独立导出 UTF-8 CSV，表头用"原范围条项"，保留完整编号（如"第一部分第1项"），命令省略 `--section`。对应表为 UTF-8 CSV，至少含"原范围条项"和"报告位置"两列。一行填一个条项和一个正文标题。一个要点涉及多处时可分行。

报告可用 Markdown 的井号标题或 Word 正文中的大纲标题。标题唯一时，"报告位置"沿用标题文字。重名时填相邻层级的路径，例如 `第二部分 股权 > 一、基本情况`，以两侧带空格的 ` > ` 分隔。仍有重名时继续补上一级。路径按实际层级核对。Word 自动编号无需手工补入。未设置大纲级别的自定义标题需人工核对。脚本列出遗漏、范围外编号及标题失效或重名的位置，供经办人复核。客户版标题沿用项目原样。

默认按工作稿检查。输出分别列出范围定位、每个标题下的正文段数及非空表格数、中英文占位符所在位置。每个标题分别列示本节占位数和含下属小节的合计。占位位置按实际出现次数列出。空标题或位置对应问题会返回非零状态，工作稿中的占位符仅提示。清洁版检查时在命令末尾加 `--final`，有占位符或残留 Word 批注时返回非零状态。工作稿可保留批注。

Markdown 的表头和分隔线、Word 中标作标题行的表头均不单独计为表格内容。Word 扫描正文、表格、批注、页眉页脚、脚注和尾注中的占位符。Markdown 读取普通段落、列表和管道表格，同一段内跨行的占位符显示起止行号。英文待填处可用 `[TBD]`、`[TBC]`、`[XX]`、`[date 1]` 或 `[insert closing date]`（匿名化建议使用"甲/乙"或 Company A，避免使用 `[XX]` 以免误判为占位符）。四类带责任人标签的批注前缀不计作占位。附图、文本框和修订痕迹按交付要求人工检查。

检查脚本默认以 UTF-8 输出结果和错误信息，重定向到文件后可按 UTF-8 打开。已显式设置的 `PYTHONIOENCODING` 优先。Windows 命令提示符若显示乱码，可在当前窗口运行 `chcp 65001` 后重试。

## 测试

```sh
python -m unittest discover -s tests -p "test_*.py"
```

单元测试覆盖 Markdown 与 Word 的标题、表格、脚注、批注和英文占位标记；`tests/test_samples.py` 用随包样稿做 7/7 的回归。修改审阅或结论规则时，另用[四句草稿](tests/review-case.md)独立试做，再按[验收要点](tests/review-criteria.md)复核。

## 隐私与使用边界

客户材料和底稿仅在当前项目授权环境中处理，不向未经授权的外部工具转发。分享本项目范例前，确认授权并脱敏，包括批注、修订记录和文件属性。

随包案例、主体及数据均为独立虚构，不使用真实客户的项目文件、金额或表格结构。实际项目按授权处理材料。

本项目在内容撰写、规则梳理与代码实现过程中，使用了 DeepSeek V4.1 Flash、GPT-6.2 Astra 和 Gemini 4 Neon 辅助；尽调方法、判断标准与最终文本由作者审定。

## 许可证

MIT License，© 2026 怪p，全文见 [LICENSE](LICENSE)。

### Word 目录交付检查

最终排版后在 Word 更新目录，逐项核对页码。对可提取正文且使用独立阿拉伯数字页脚的终稿，可另用 `pdftotext -layout final.pdf final-layout.txt` 加 `python scripts/check_word_toc.py final.docx final-layout.txt`。脚本不能核对的版式转为 Word 人工核对，不能跳过。
