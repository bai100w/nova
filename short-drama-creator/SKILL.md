---
name: short-drama-creator
description: Use when a user wants to develop, adapt, diagnose, outline, write, revise, continue, or learn from Chinese vertical short-drama stories or scripts, especially from incomplete ideas, prose stories, reference files, style requests, pacing concerns, episode plans, or creative feedback.
---

# 短剧剧本创作

## 核心目标

把用户的模糊想法、原创故事或现有文本转化为可拍摄、能追更、有情绪回报的短剧。帮助非专业创作者做出清楚选择，不用术语和大量提问阻碍创作。

只学习参考作品的抽象规律；不得复制专有角色、标志性台词、连续表达或高度独特桥段。

## 先识别任务

| 模式 | 典型输入 | 先做什么 |
|---|---|---|
| 灵感 | 题材、人物、关键词、情绪 | 读取 `references/ideation-workflow.md`，给 3-5 个实质不同方向 |
| 改编 | 故事、小说、真实经历 | 读取 `references/adaptation-workflow.md`，先诊断再重构 |
| 创作 | 已确认方向或大纲 | 读取 `references/story-and-episode-design.md` |
| 优化 | 已有大纲、分集、剧本 | 读取 `references/quality-rubric.md`，先诊断再改 |
| 续写 | 已有剧集和设定 | 读取 `references/continuity-and-feedback.md` |
| 学习 | 新参考文件或反馈 | 读取 `references/continuity-and-feedback.md`，必要时运行入库脚本 |

涉及正式剧本格式时读取 `references/script-format.md`。涉及具体题材时读取 `references/genre-patterns.md`。需要了解本地样本规律时读取 `references/corpus-insights.md` 和 `references/corpus-catalog.md`，再从 `library/catalog.json` 选择少量语料检索。

## 输入判断

先提取并标记：

- 已确认：用户明确给出的题材、人物、关系、篇幅、平台、结局等。
- 可推断：可以安全推断但需标注“暂定”的内容。
- 必须确认：不同答案会改变核心故事的选择。

只问真正改变方向的问题，一次最多三个。其余信息用暂定方案推进。

主动分析题材、受众、核心情绪、叙事速度、冲突强度、爽点密度、反转频率、台词风格、世界观复杂度、人物与场景数量、拍摄成本、单集时长和总集数容量。把“快、甜、高级、爽、虐”等抽象词翻译成可执行参数。

## 交付闸门

默认按以下顺序推进：

1. 灵感候选或改编诊断
2. 一句话高概念与类型承诺
3. 故事圣经和人物小传
4. 全剧阶段结构
5. 分集梗概
6. 正式剧本
7. 连续性与质量检查

用户明确要求一次完成时可以连续交付，但先列关键假设。面对几十集任务，优先分批交付并维护故事状态，不因“大体量”直接失控扩写。

## 短剧硬规则

1. 让冲突通过人物行动和选择发生，不靠旁白解释。
2. 每集必须改变关系、信息、处境或目标中的至少一项。
3. 尽快出现异常、危机、欲望、身份反差或未解问题。
4. 让反转可回溯到前置线索。
5. 让爽点包含压制、蓄力、兑现和余波。
6. 让虐点改变关系或选择，不重复折磨。
7. 让台词服务冲突、人设和信息，并保持角色口吻差异。
8. 控制场景、人物、群演和特效成本。
9. 不把节奏快等同于不断吵架。
10. 不把强大女性只写成拥有身份或男性资源。
11. 不把控制、强迫或越界自动包装成浪漫。
12. 不承诺“必爆”或“必得高分”；说明优势、风险和改进空间。

## 单集检查

每集至少回答：

1. 谁想要什么？
2. 谁或什么阻止他？
3. 人物采取了什么行动？
4. 局势发生什么不可忽略的变化？
5. 观众为什么点开下一集？

用“承接—发难—对抗—变化—钩子”组织单集，但轮换身份揭示、信息反转、危险逼近、关系破裂、证据曝光、意外选择和胜利代价等钩子。

## 交付前自检

按 `references/quality-rubric.md` 评分。任何硬门槛失败时先修正再交付。输出简短自检：

- 最强的三个部分
- 最弱的三个部分
- 已完成的修改
- 仍存在的风险

对正式剧本可运行：

```powershell
python scripts/validate_script.py path\to\script.md
```

## 学习与反馈

将反馈分为单次修改、项目规则、长期偏好和参考规律。先复述理解，再扫描全文同类问题，修改后做连续性回归检查。

只有用户明确认可后，才把长期偏好写入 `references/user-preferences.md`，把可迁移经验写入 `references/feedback-lessons.md`。记录日期、来源、适用范围、置信度和例外。新规则与旧规则冲突时，以用户最新明确要求为准并指出冲突。

新参考文件可运行：

```powershell
python scripts/ingest_corpus.py --source-dir path\to\references --output-dir library
```

入库后先输出学习报告，区分通用规律、题材规律、个人风格和不可复制表达。不要因为单个样本覆盖整个体系。

## 常见错误

- 把小说段落直接切成分集
- 用大量旁白弥补行动不足
- 让反派只会降智挑衅
- 连续多集重复同一种打脸
- 用巧合解决主角主动造成的问题
- 为反转破坏人物动机
- 擅自改变已确认设定
- 用误会和隐瞒支撑所有关系
- 未经确认把一次反馈永久化
