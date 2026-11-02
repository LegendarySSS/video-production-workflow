# 项目数据约定

project-template.json 是起点，不是已完成项目，也不是自动执行程序。null 表示未知，空数组表示尚无条目；不要用虚构路径填满模板。可以按项目增加字段，保留已有有效数据。项目路径优先相对 project.json，外部路径注明访问依赖。

## 常用条目

- tools：tool_id、用途、实际可用能力、输入限制、manual 或 connected、核实来源。未连接工具只能记录外部步骤。
- assets：asset_id、path、kind、version、status、origin、usage_authorization。status 为 draft、approved、needs_review 或 missing。
- characters：character_id、name、identity、approved_reference_ids、test_results。identity 写可观察的固定特征。
- scenes：scene_id、layout_asset_id、lighting、character_states、prop_states。角色状态包含服装等可变项，注明左右坐标约定。
- shots：shot_id、scene_id、character_ids、purpose、duration_seconds、framing、action、camera、audio、reference_asset_ids、state_in、state_out、status、selected_generation_id。
- generations：generation_id、shot_id、version、tool_id、model、parameters、prompt、input_asset_ids、output_path、created_at、cost、review。按实际支持情况记录参数。
- review：各维度的结果和证据、checked_by、checked_at、accepted_exceptions。维度见一致性参考文档。
- decisions：decision_id、scope、subject_id、decision、source、created_at、affected_ids。scope 默认 project；source 区分用户确认与助手提案。
- documents：document_id、kind、path、version、status。保存剧本、时间轴或剪辑表的位置。
- music.sections：section_id、label、start_seconds、end_seconds、emotion、beat_notes。
- deliverables：path、version、specifications、review_status、unverified_checks。

## 状态

镜头可以使用 draft → keyframe_ready → ready_to_generate → generated → reviewed → approved。
需要外部操作时用 awaiting_external；输入改变或衔接失效用 needs_review；验收失败用 rejected。恢复制作以实际素材与验收记录为准，不能机械跳状态。

## 写入前检查

- ID 在所属集合内唯一，引用真实存在；选中候选属于对应镜头，生成输入引用真实素材。
- 时长为正数；时间段起点不小于零且终点大于起点。无重叠设计的连续时间轴检查缺口和重叠。
- 总时长按最终时间轴计算，转场重叠计入；不能把所有源素材时长直接求和当成片时长。
- 缺失值保留未知，实际成本与估计分开，不以 0 表示未知费用。
- approved 素材存在且有检查依据；未执行检查明确记录。
- 写入临时文件、解析成功、保留上版后替换。多人同时编辑先重新读取并核对版本，冲突时保留双方变更再处理。
