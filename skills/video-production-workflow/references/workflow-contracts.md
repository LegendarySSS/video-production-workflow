# 阶段交接与上下文

本文件定义人工/Agent 执行约定，不是后台任务引擎。scripts/workflow.py 是只读辅助检查，不能阻止绕过它的调用，不计费、不自动批准或转换状态。

## 当前任务读取范围

先看 brief、state 与 decisions 中的相关决定。分镜读取本场戏；单镜头读取指定 shots、其角色/场次、批准资产、选中候选与前后相邻镜头。相关文件按路径定位，不把整部作品、案例全文、历史失败候选放入每次上下文。项目很大时用脚本筛选 JSON；脚本仍在本机读取整个 JSON，不承诺数据库级扩展性。

实际需要某个交接的输入文档时再读正文。恢复时检查版本与文件存在，不能只读摘要就批准镜头。

## 阶段输入与输出

| stage | 输入 | 输出与检查 |
|---|---|---|
| brief | 用户需求、实际工具 | brief、delivery_contract、未知项；足以开始文案 |
| story | 简报、相关决定、指定音频 | 版本化剧本/段落表；时长测量或估算依据 |
| design | 剧本场次、视觉目标 | characters/scenes/assets；批准基准与尚未测试的角度 |
| storyboard | 剧本、角色场景、相关参考 | shots、预演、案例索引；空间、动作、时长检查 |
| production | 本镜头、批准参考、授权、任务记录 | 代表性试镜/候选、generations/review；动态播放证据 |
| post | 选中候选、时间轴、交付约定 | 成片或剪辑表、deliverables；完整播放与未检查项 |

任务规模小可合并文档；不适用阶段在 unresolved/decisions 中说明，不制造空产物。首次动态试镜属于 production，不能因为尚无试镜而阻止其自身制作；通过后才扩大批量。

## handoffs 条目

每次交接包含：handoff_id、stage、status、input_versions、outputs、evidence、unresolved、next_action。

- status 为 draft、ready、needs_review 或 blocked。ready 代表本阶段已按范围检查，可交接；不代表用户同意付费或成片验收通过。
- input_versions 为 {id, version} 列表，ID 指向 documents/assets/characters/scenes/shots 中实际条目。引用对象必须有显式 version；不以文件名暗示版本。
- outputs 为项目内相对文件路径列表；不能放 URL、凭证或项目外路径。参考库外部链接存 reference_cases 的 source，不作为已产出的项目文件。
- evidence 为非空检查说明列表，写检查范围与依据；未执行的检查写 unresolved。文字存在不证明检查真实。
- next_action 写可以继续的具体动作。保存新的交接记录，原记录用于追溯。

输入版本改变时检查所有交接 input_versions，沿其输出对应的文档/资产再追踪下游；将受影响条目标 needs_review。同时检查角色/场景引用、shots.reference_asset_ids 和 selected_generation_id 等生产依赖；脚本不自动完成整张依赖图的传播。

## 离线辅助

在项目目录执行，脚本使用安装后的真实绝对路径：

```bash
python3 /真实路径/video-production-workflow/scripts/workflow.py context --project project.json --shot S003
python3 /真实路径/video-production-workflow/scripts/workflow.py check --project project.json --stage storyboard
```

context 返回当前镜头及相邻镜头、涉及角色场景、引用资产、选中候选和关联决定，省略候选提示词/私密 URL；不是自动发送给供应商。输出仍可能含剧情隐私，不公开分享。找不到镜头报错，不回退到全项目。

check 核对唯一 ID、引用、选中候选归属、ready 交接的产物存在与输入版本一致。--stage 还要求该阶段至少有一个 ready 交接；默认仅检查结构，不要求初始模板就有全部阶段产物。输出问题与退出码 2 表示需处理；0 仅表示所检查结构通过，不保证预算、表演、授权或成片质量。
