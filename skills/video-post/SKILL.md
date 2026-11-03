---
name: video-post
description: 对已选视频素材组织剪辑、声音与字幕，检查镜头连续性、动态表演和交付规格。适用于后期与成片验收；没有剪辑或播放能力时明确交付清单与未检查项。
metadata:
  version: "0.3.0"
---

# 后期与交付验收

本技能属于视频制作套件，需与 video-production-workflow 一起安装。先定位 [共享项目约定](../video-production-workflow/references/project-data.md) 和 [阶段交接](../video-production-workflow/references/workflow-contracts.md)。路径不同按技能名定位；缺共享文件则报告不完整安装，不编造依赖已加载。单项任务只执行本范围，不自动启动整片制作。

读取输入：选中素材、剪辑/音乐时间轴、交付约定、相关 review 与场记。读取 [一致性验收](../video-production-workflow/references/continuity-and-review.md)，动态短剧同时读取 [动态要求](../video-production-workflow/references/dynamic-drama.md)。

- 按实际工具剪辑；没有剪辑工具提供版本化剪辑表，不声称输出影片。音乐、配音、字幕工具分别盘点，不因视频 API 存在就假定齐全。
- 检查动作接点、身份、空间、色彩曝光、对白/声音与剪辑节奏；字幕检查文字、说话者、时间、安全区域与目标画幅。
- 总时长按最终时间轴计算并计入转场重叠；音画同步和运动检查需要完整播放，抽帧仅作筛查。
- 未通过的问题按来源返回剧本、设定、分镜、镜头或本阶段，列具体影响范围；不一律重新生成。
- previsualization 与 still_image 不自动升级为动态成片；艺术性停格可保留并注明用途。
- 输出实际成片/剪辑表、规格、检查位置和未检查项。完成是针对约定交付形态，pending 不能写成 pass，API 状态不能当质量证明。

## 交接

保存本阶段产物及输入版本，记录 evidence、unresolved 和下一个动作。不得以文档存在代替语义验收；沿用总入口的凭证保护、预算、版本保存和动态交付约束。
