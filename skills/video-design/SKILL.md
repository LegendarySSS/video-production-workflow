---
name: video-design
description: 建立或修改视频角色身份、视觉设定、场景布局与场记，维护批准参考资产及相关镜头依赖。适用于人物与画面一致性任务；不负责剧本重写。
metadata:
  version: "0.3.0"
---

# 角色与视觉设定

本技能属于视频制作套件，需与 video-production-workflow 一起安装。先定位 [共享项目约定](../video-production-workflow/references/project-data.md) 和 [阶段交接](../video-production-workflow/references/workflow-contracts.md)。路径不同按技能名定位；缺共享文件则报告不完整安装，不编造依赖已加载。单项任务只执行本范围，不自动启动整片制作。

读取输入：brief、相关剧本场次、characters、scenes 与批准 assets。读取 [一致性与验收](../video-production-workflow/references/continuity-and-review.md) 的角色和场次部分。

- 固定身份与服装、伤痕、持物等场次状态分开；记录画面左右、人物自身左右和空间坐标。
- 先确定身份基准，再补本片需要的角度与表情，各图分别核对；不因同一批生成就视作同一人。
- 画面风格写成色彩、光线、材质、构图与景深等可观察约束，导演姓名不能代替执行规格。
- 只使用实际可用的图片工具；无工具交付设定与输入规格，未生成资产不编路径。私有参考上传依照已有授权。
- 输出批准或待审的角色与场景资产、测试结果、版本及未验证机位。变更时列出依赖镜头，标 needs_review，保留旧批准与版本。

## 交接

保存本阶段产物及输入版本，记录 evidence、unresolved 和下一个动作。不得以文档存在代替语义验收；沿用总入口的凭证保护、预算、版本保存和动态交付约束。
