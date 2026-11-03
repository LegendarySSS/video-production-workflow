#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


COLLECTIONS = {
    'documents': 'document_id', 'assets': 'asset_id', 'characters': 'character_id',
    'scenes': 'scene_id', 'shots': 'shot_id', 'generations': 'generation_id',
    'handoffs': 'handoff_id', 'reference_cases': 'case_id',
}
STAGES = ('brief', 'story', 'design', 'storyboard', 'production', 'post')


def index_project(project):
    if not isinstance(project, dict):
        raise ValueError('项目顶层必须是对象')
    indexed = {}
    for collection, field in COLLECTIONS.items():
        records = project.get(collection, [])
        if not isinstance(records, list):
            raise ValueError(f'{collection} 必须是数组')
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f'{collection} 条目必须是对象')
            identifier = record.get(field)
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError(f'{collection} 缺少有效 {field}')
            if identifier in indexed:
                raise ValueError(f'重复 ID: {identifier}')
            indexed[identifier] = (collection, record)
    return indexed


def local_file(root, value):
    if not isinstance(value, str) or not value or '://' in value:
        raise ValueError('产物必须是项目内相对文件路径')
    relative = Path(value)
    resolved = (root / relative).resolve()
    if relative.is_absolute() or not resolved.is_relative_to(root.resolve()):
        raise ValueError('产物路径不能离开项目目录')
    if not resolved.is_file():
        raise ValueError('产物文件不存在')
    return resolved


def check_project(project, root, stage=None):
    indexed = index_project(project)
    issues = []

    def reference(identifier, collection, owner):
        if identifier is None:
            return
        if not isinstance(identifier, str) or indexed.get(identifier, (None,))[0] != collection:
            issues.append(f'{owner}: 无有效 {collection} 引用 {identifier}')

    for shot in project.get('shots', []):
        identifier = shot['shot_id']
        reference(shot.get('scene_id'), 'scenes', identifier)
        for collection, field in (('characters', 'character_ids'), ('assets', 'reference_asset_ids')):
            values = shot.get(field, [])
            if not isinstance(values, list):
                issues.append(f'{identifier}: {field} 必须是数组')
                continue
            for value in values:
                reference(value, collection, identifier)
        selected = shot.get('selected_generation_id')
        reference(selected, 'generations', identifier)
        if isinstance(selected, str) and indexed.get(selected, (None,))[0] == 'generations':
            if indexed[selected][1].get('shot_id') != identifier:
                issues.append(f'{identifier}: 选中候选属于其他镜头')
    for character in project.get('characters', []):
        for asset_id in character.get('approved_reference_ids', []):
            reference(asset_id, 'assets', character['character_id'])
    for scene in project.get('scenes', []):
        reference(scene.get('layout_asset_id'), 'assets', scene['scene_id'])
    for case in project.get('reference_cases', []):
        for shot_id in case.get('related_shot_ids', []):
            reference(shot_id, 'shots', case['case_id'])
        if case.get('analysis_path'):
            try:
                local_file(root, case['analysis_path'])
            except ValueError as error:
                issues.append(f'{case["case_id"]}: {error}')
    for generation in project.get('generations', []):
        if not generation.get('shot_id'):
            issues.append(f'{generation["generation_id"]}: 缺少 shot_id')
        else:
            reference(generation['shot_id'], 'shots', generation['generation_id'])
    for handoff in project.get('handoffs', []):
        identifier = handoff['handoff_id']
        if handoff.get('stage') not in STAGES:
            issues.append(f'{identifier}: 无效 stage')
        if handoff.get('status') not in ('draft', 'ready', 'needs_review', 'blocked'):
            issues.append(f'{identifier}: 无效 status')
        if handoff.get('status') != 'ready':
            continue
        for field in ('outputs', 'evidence'):
            values = handoff.get(field)
            if not isinstance(values, list) or not values or not all(isinstance(item, str) and item.strip() for item in values):
                issues.append(f'{identifier}: ready 交接需要非空 {field} 字符串数组')
        outputs = handoff.get('outputs', [])
        for output in outputs if isinstance(outputs, list) else []:
            try:
                local_file(root, output)
            except ValueError as error:
                issues.append(f'{identifier}: {error}')
        if not isinstance(handoff.get('next_action'), str) or not handoff['next_action'].strip():
            issues.append(f'{identifier}: 缺少 next_action')
        versions = handoff.get('input_versions', [])
        if not isinstance(versions, list):
            issues.append(f'{identifier}: input_versions 必须是数组')
            continue
        for dependency in versions:
            if not isinstance(dependency, dict) or not isinstance(dependency.get('id'), str):
                issues.append(f'{identifier}: 无效输入版本条目')
                continue
            target = indexed.get(dependency['id'])
            if target is None or target[0] not in ('documents', 'assets', 'characters', 'scenes', 'shots'):
                issues.append(f'{identifier}: 输入引用不存在或类型错误')
            elif dependency.get('version') is None or target[1].get('version') is None or dependency['version'] != target[1]['version']:
                issues.append(f'{identifier}: 输入 {dependency["id"]} 版本失效或缺失')
    if stage and not any(item.get('stage') == stage and item.get('status') == 'ready' for item in project.get('handoffs', [])):
        issues.append(f'{stage}: 尚无 ready 交接')
    return {'structure_passed': not issues, 'issues': issues, 'quality_verified': False}


def shot_context(project, identifier):
    indexed = index_project(project)
    if indexed.get(identifier, (None,))[0] != 'shots':
        raise ValueError('指定镜头不存在')
    shots = project.get('shots', [])
    position = next(index for index, shot in enumerate(shots) if shot['shot_id'] == identifier)
    selected_shots = shots[max(0, position - 1):position + 2]
    character_ids = {value for shot in selected_shots for value in shot.get('character_ids', [])}
    scene_ids = {shot.get('scene_id') for shot in selected_shots}
    characters = [item for item in project.get('characters', []) if item['character_id'] in character_ids]
    scenes = [item for item in project.get('scenes', []) if item['scene_id'] in scene_ids]
    asset_ids = {value for shot in selected_shots for value in shot.get('reference_asset_ids', [])}
    asset_ids.update(value for character in characters for value in character.get('approved_reference_ids', []))
    asset_ids.update(scene.get('layout_asset_id') for scene in scenes)
    selected_ids = {shot.get('selected_generation_id') for shot in selected_shots}
    subject_ids = character_ids | scene_ids | asset_ids | {shot['shot_id'] for shot in selected_shots}
    subject_ids.discard(None)
    decisions = project.get('decisions', [])
    if not isinstance(decisions, list):
        raise ValueError('decisions 必须是数组')
    generation_fields = ('generation_id', 'shot_id', 'version', 'output_path', 'task_record_path', 'review')
    return {
        'project_id': project.get('project_id'), 'brief': project.get('brief'),
        'state': project.get('state'), 'delivery_contract': project.get('delivery_contract'),
        'focus_shot_id': identifier, 'shots': selected_shots, 'characters': characters, 'scenes': scenes,
        'assets': [item for item in project.get('assets', []) if item['asset_id'] in asset_ids],
        'generations': [{key: item[key] for key in generation_fields if key in item}
                        for item in project.get('generations', []) if item['generation_id'] in selected_ids],
        'decisions': [item for item in decisions if isinstance(item, dict) and
                      (item.get('subject_id') in subject_ids or
                       any(value in subject_ids for value in item.get('affected_ids', [])) or
                       not item.get('subject_id') and not item.get('affected_ids'))],
        'reference_cases': [item for item in project.get('reference_cases', [])
                            if any(shot['shot_id'] in item.get('related_shot_ids', []) for shot in selected_shots)],
        'note': '相邻镜头按 shots 数组顺序确定；实际剪辑顺序不同时另读时间轴。仅筛选数据，不验证艺术质量。',
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description='只读项目交接检查和镜头上下文提取，不调用网络')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('context', 'check'):
        command = commands.add_parser(name)
        command.add_argument('--project', required=True)
        if name == 'context':
            command.add_argument('--shot', required=True)
        else:
            command.add_argument('--stage', choices=STAGES)
    args = parser.parse_args(arguments)
    try:
        path = Path(args.project).resolve()
        project = json.loads(path.read_text(encoding='utf-8'))
        result = shot_context(project, args.shot) if args.command == 'context' else check_project(project, path.parent, args.stage)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get('issues') else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        message = str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else '项目文件无法读取或结构错误'
        print(json.dumps({'error': message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
