---
name: overseas-social-mining
description: Use when researching overseas social media signals, trends, creators, communities, UGC, hashtags, keywords, VOC, content opportunities, or HTML reports for a product, brand, person, IP, event, scene, or cultural tag.
---

# 海外社媒挖掘

## 核心原则

先识别对象，先路由平台，再深挖内容。全平台覆盖指路由器认识主流平台机制，不代表每次扫描所有平台。

## 单关键词入口契约

当用户只输入一个关键词、短标签或名称时，不要直接开始研究，也不要直接交付空白或示例 HTML。先把关键词当作待确认的对象，给出一轮最小引导：

> 我先确认 4 项：①它是商品/品牌、人名、IP、事件，还是场景标签？②目标市场/语言（不知道可回复“全球”）？③时间窗（默认近 90 天）？④研究目标（趋势、创作者、VOC、内容机会或综合）？

可以先根据词形给出“暂定对象类型”，但必须标注为待确认；人物和 IP 在确认前不得下声量、受众或争议结论。用户补齐后再开始挖掘，并按 HTML 报告契约生成可下载的单文件 HTML；如果用户明确要求直接开始，仍需把未提供字段写入对象卡并采用默认值，同时在报告中标注假设。

## 强制流程

1. 建对象卡：类型、市场、语言、时间窗、目标、别名和消歧状态。读 [entity-and-query-expansion.md](references/entity-and-query-expansion.md)。人物或 IP 未完成必要消歧时，不得进入声量、受众或争议结论。
2. 建查询树后做低成本平台探测。读 [platform-routing.md](references/platform-routing.md)。不得仅凭经验直接宣布主阵地。
3. 默认只深挖 2–3 个主挖平台和 1 个交叉验证平台；有明确国家/语言理由时再加 1 个区域平台。建立“已排除平台”表并写明探测证据和理由。
4. 只读取入选平台对应的 [platform-playbooks.md](references/platform-playbooks.md) 章节。平台功能、规则和发现入口可能变化，使用前核对当前官方信息。
5. 建证据账本并读 [evidence-and-scoring.md](references/evidence-and-scoring.md)。每个关键事实保留链接、采集日期、市场、样本、指标定义和证据类型。播放、互动、帖子、排名、搜索热度等代理指标不得称为销量、GMV 或转化。
6. 聚类趋势、Meme、UGC、创作者/社区、语言和 VOC，再读 [analysis-and-opportunities.md](references/analysis-and-opportunities.md) 形成内容公式、机会、风险和行动计划。
7. 用户要求报告时，读 [html-report-contract.md](references/html-report-contract.md)，复制并填充 [overseas-social-report-template.html](assets/overseas-social-report-template.html)。正式报告不得用虚构数字或示例链接补空位。验证脚本必须以当前 Skill 根目录解析为绝对路径，再用环境中可用的真实 Python 运行；只有退出码 0 且输出包含 `OK:` 才算通过，不能把无输出当成功。
8. 完成前核对：对象无混淆、路由可解释、已排除平台表齐全、证据可追溯、平台指标未被强行横比、弱信号已降级、HTML 可离线阅读。

## 快速路由

| 输入 | 首轮候选机制 | 必查风险 |
|---|---|---|
| 商品/品牌 | 短视频、视觉灵感、长视频、社区讨论 | 热度冒充销量、广告混入自然内容 |
| 人物 | 职业、实时话题、视频、社区 | 同名混合、敏感属性推断 |
| 娱乐/游戏 IP | 短视频、视频/直播、实时话题、社区 | 错译、官方/二创混合、版权 |
| B2B/技术 | 专业网络、长视频、论坛、实时话题 | 互动少被误判为无需求 |
| 审美/场景 | 视觉灵感、短视频、搜索验证 | 泛词污染、季节性 |
| 实时事件 | 实时话题、论坛、视频 | 突发峰值冒充长期趋势 |

## 示例

输入“某游戏 IP”且没有统一英文名时，先扩展官方名、音译、角色、阵营、关系/CP、剧情、版本和二创格式；轻探测若显示 YouTube/Twitch 有持续攻略直播、Reddit/Discord 有稳定社区、TikTok 仅有短期剪辑峰值，则选择 YouTube、Twitch、Reddit 为主挖，TikTok 为验证，记录 Instagram/X 等平台的排除或降级理由。不得把“没有统一英文标签”写成“海外无热度”。

## 常见错误

- 机械搜遍所有平台：回到路由探测和平台预算。
- 默认最热门搜索结果就是目标人物：回到同名消歧门。
- 并排展示原始播放量形成伪排名：改用平台内分位和证据质量。
- 只搜标签不读评论/社区语言：补 VOC、黑话和反向词。
- 用泛泛版权免责声明代替决策：分成可做、需授权、不建议。
- 数据取不到就补常识：标为未取得证据并停止扩张。

## 停止条件

同名未解、两轮查询仍无有效信号、访问控制阻断、指标定义不明或关键证据互相矛盾时，停止强结论，交付已知、未知、置信度和下一步验证。
