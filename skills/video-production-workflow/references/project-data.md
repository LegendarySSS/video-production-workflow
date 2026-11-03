# 项目数据约定

project-template.json 是起点，不是已完成项目，也不是自动执行程序。null 表示未知，空数组表示尚无条目；不要用虚构路径填满模板。可以按项目增加字段，保留已有有效数据。项目路径优先相对 project.json，外部路径注明访问依赖。

## 常用条目

- tools：tool_id、用途、实际可用能力、输入限制、manual 或 connected、核实来源。未连接工具只能记录外部步骤。
- assets：asset_id、path、kind、version、status、origin、usage_authorization。status 为 draft、approved、needs_review 或 missing。
- characters：character_id、name、identity、approved_reference_ids、test_results。identity 写可观察的固定特征。
- scenes：scene_id、layout_asset_id、lighting、character_states、prop_states。角色状态包含服装等可变项，注明左右坐标约定。
- delivery_contract：target_kind、execution_mode、required_performance、sample_test。target_kind 区分 dynamic_video、previsualization、static_storyboard、motion_comic；execution_mode 为 connected_video、external_video、live_action、animation 或 preproduction_only。sample_test 记录状态、工具、素材路径、检查证据和未检查项。
- shots：shot_id、scene_id、character_ids、purpose、duration_seconds、framing、action、camera、audio、reference_asset_ids、state_in、state_out、performance_beats、dialogue_timing、motion_source、status、selected_generation_id。
- generations：generation_id、shot_id、version、tool_id、model、parameters、prompt、input_asset_ids、output_path、task_record_path、task_id、created_at、cost、review。按实际支持情况记录参数。
- review：各维度的结果和证据、checked_by、checked_at、accepted_exceptions。维度见一致性参考文档。
- decisions：decision_id、scope、subject_id、decision、source、created_at、affected_ids。scope 默认 project；source 区分用户确认与助手提案。
- documents：document_id、kind、path、version、status。保存剧本、时间轴或剪辑表的位置。
- music.sections：section_id、label、start_seconds、end_seconds、emotion、beat_notes。
- deliverables：path、version、specifications、review_status、unverified_checks。

## 状态

镜头可以使用 draft → keyframe_ready → ready_to_generate → generated → reviewed → approved。
需要外部操作时用 awaiting_external；输入改变或衔接失效用 needs_review；验收失败用 rejected。恢复制作以实际素材与验收记录为准，不能机械跳状态。

motion_source 按实际来源填写 generated_video、live_action、animation 或 still_image；单图导出的 MP4 仍属于 still_image。performance_beats 按时间描述说话、表情、视线和动作，不凭填表认定素材完成。

## 写入前检查

- ID 在所属集合内唯一，引用真实存在；选中候选属于对应镜头，生成输入引用真实素材。
- 时长为正数；时间段起点不小于零且终点大于起点。无重叠设计的连续时间轴检查缺口和重叠。
- 总时长按最终时间轴计算，转场重叠计入；不能把所有源素材时长直接求和当成片时长。
- 缺失值保留未知，实际成本与估计分开，不以 0 表示未知费用。
- approved 素材存在且有检查依据；未执行检查明确记录。
- 写入临时文件、解析成功、保留上版后替换。多人同时编辑先重新读取并核对版本，冲突时保留双方变更再处理。

- 动态短剧交付需核对 delivery_contract 和完整播放证据；previsualization、静态素材合成和未完成的表演检查不能标为动态成片已验收。缺少动态来源时 state.status 为 awaiting_external，next_action 列出具体外部执行步骤。

内置 API 的 task.json 记录执行状态，project.json 记录制作决定，两者通过 task_record_path 关联。网络提交状态不明时保留 submission_unknown，不把新目录当作自动重试；生成成功的素材仍需 review。

## V0.3.0 阶段交接与参考

新增 handoffs 与 reference_cases，定义见 [阶段交接](workflow-contracts.md) 及 [参考分析](../../video-storyboard/references/reference-analysis.md)。被 input_versions 引用的 documents/assets/characters/scenes/shots 条目需显式 version。剧本改变不覆盖旧批准依据，保存新版本并检查依赖。

reference_cases 保存 case_id、narrative_problem、tags、source、analysis_path、related_shot_ids；具体观察、分析与改编保存在 analysis_path 指向的案例文件。来源不可核实时明确标 unverified，实际未阅读的内容不生成分析。
