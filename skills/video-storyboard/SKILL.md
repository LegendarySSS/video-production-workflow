---
name: video-storyboard
description: 将剧本或音乐结构转成可执行镜头表，分析电影、分镜稿、剧本或漫画参考，设计表演、空间和镜头衔接。适用于分镜与参考分析；不把静态预演当成动态成片。
metadata:
  version: "0.3.0"
---

# 分镜与表演调度

本技能属于视频制作套件，需与 video-production-workflow 一起安装。先定位 [共享项目约定](../video-production-workflow/references/project-data.md) 和 [阶段交接](../video-production-workflow/references/workflow-contracts.md)。路径不同按技能名定位；缺共享文件则报告不完整安装，不编造依赖已加载。单项任务只执行本范围，不自动启动整片制作。

读取输入：当前剧本/音乐结构、相关角色与场次、批准参考和交付约定；只读取本场戏及必要的前后衔接。短剧读取 [动态要求](../video-production-workflow/references/dynamic-drama.md)。

需要已有作品参考时，读取 [参考分析方法](references/reference-analysis.md)，按 [案例模板](assets/reference-case-template.json) 保存分析。参考不是必需前置条件：资料不可用时明确缺口，继续原创分镜，不编造原稿或作者意图。

- 先写本场戏需要观众知道什么、感受什么，再安排镜头。每镜头记录 purpose、duration_seconds、framing、action、camera、audio、state_in/out、performance_beats、dialogue_timing 与实际资产引用。
- 视线、轴线、人物位置、动作接点与道具归属可检查；有意跳切等写明目的。
- 将参考手法改写为本片角色与空间中的动作，漫画格间省略的动作需要补成可发生的时间过程；导演姓名不作为唯一分镜依据。
- 对复杂动作比较拆镜、参考控制、实拍/动画等路径，服从艺术目标、预算与用户技术路线。
- 先做关键帧/时间轴预演，标 previsualization；无播放能力不宣称节奏已验证。选择覆盖实际风险的动态试镜，交给镜头制作专项。
- 输出 shots、分镜文档、参考案例索引及依赖版本；参考案例通过 case_id 关联镜头，不加载整库。

## 交接

保存本阶段产物及输入版本，记录 evidence、unresolved 和下一个动作。不得以文档存在代替语义验收；沿用总入口的凭证保护、预算、版本保存和动态交付约束。
