# nova
主要存放nova的个人skill，规范工作流的同时分享经验

## 剧集 skill 套组 V4.0

[完整套组与说明](drama-suite-v4.0/README.md) · [版本记录](drama-suite-v4.0/CHANGELOG.md)

覆盖真人短剧、3DCG、2D 动画与漫剧。保留全套目录及相对引用，不绑定特定生成模型。

| 界面名称 | 调用名 |
|---|---|
| 剧集总控 | `$drama-control` |
| 剧本 | `$drama-script` |
| 导演与视觉开发 | `$drama-direction` |
| 资产 | `$drama-assets` |
| 分镜 | `$drama-storyboard` |
| 生成与审片 | `$drama-production` |
| 剪辑与后期 | `$drama-editing` |
| 宣发物料 | `$drama-materials` |
| 参考学习与复盘 | `$drama-learning` |

安装时把 `drama-suite-v4.0/` 中九个 `drama-*` 目录放到 Codex 的用户级 `skills/` 下，保持它们同级；`examples/` 可一同保留，README 与 CHANGELOG 随发布包归档。已有同名模块应先备份并整体替换，避免新旧文件混在一起。日常从 `$drama-control` 开始即可。

版本验证边界：本包已试跑到预演阶段；生成、后期和宣发尚未完成端到端模型实跑。结构与引用校验不能代替成片质量验证。
