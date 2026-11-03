---
name: video-shot-production
description: 依据已准备的角色、场次与分镜执行动态试镜或逐镜头视频生成，管理候选、任务恢复及返工。适用于实际镜头制作；缺视频能力时只交付外部输入包。
metadata:
  version: "0.3.0"
---

# 动态镜头制作

本技能属于视频制作套件，需与 video-production-workflow 一起安装。先定位 [共享项目约定](../video-production-workflow/references/project-data.md) 和 [阶段交接](../video-production-workflow/references/workflow-contracts.md)。路径不同按技能名定位；缺共享文件则报告不完整安装，不编造依赖已加载。单项任务只执行本范围，不自动启动整片制作。

读取输入：本镜头、相邻镜头衔接、相关角色/场景、批准资产、预算授权和已有任务记录。必须读取 [动态要求](../video-production-workflow/references/dynamic-drama.md)、[一致性验收](../video-production-workflow/references/continuity-and-review.md)；调用 API 再读 [API 配置](../video-production-workflow/references/api-setup.md)。

现有三家客户端保存在 ../video-production-workflow/scripts/video.py；使用真实绝对路径，密钥/请求/任务放项目目录。先 doctor 与离线 preview，按明确授权 submit 一次；等待超时查原任务，submission_unknown 核对后 attach，不自动重提。--confirm-spend 不是费用上限。

- 先播放验收代表性动态试镜，再批量制作；必要口型与对白同步未验证时不得默认通过。
- 视频工具不支持某项参考或音频时明确拒绝/调整方案，不静默丢弃、不用静帧配音冒充动态表演。
- 按授权尝试次数与费用范围停止，无法确认剩余额度时不继续付费。成本未知留 null，不能用估计充当实付。
- 为每个候选保存版本、输入引用、实际参数、任务记录路径和输出；API succeeded 与下载成功仍是 quality_review pending。
- 无动态来源记录 awaiting_external；无播放能力保留未检查项。输出候选与检查证据，选中版本关联 selected_generation_id 后交后期。

## 交接

保存本阶段产物及输入版本，记录 evidence、unresolved 和下一个动作。不得以文档存在代替语义验收；沿用总入口的凭证保护、预算、版本保存和动态交付约束。
