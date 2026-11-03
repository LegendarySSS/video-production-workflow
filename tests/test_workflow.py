import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/video-production-workflow/scripts'))
from workflow import check_project, shot_context


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'story.md').write_text('已检查的剧本')
        self.project = {
            'documents': [{'document_id': 'D1', 'version': 2}],
            'characters': [{'character_id': 'C1', 'approved_reference_ids': ['A1']}],
            'assets': [{'asset_id': 'A1'}, {'asset_id': 'A2'}],
            'shots': [{'shot_id': f'S{index}', 'character_ids': ['C1'] if index == 2 else []}
                      for index in range(5)],
            'handoffs': [{'handoff_id': 'H1', 'stage': 'story', 'status': 'ready',
                          'input_versions': [{'id': 'D1', 'version': 2}],
                          'outputs': ['story.md'], 'evidence': ['朗读测时已记录'],
                          'next_action': '制作分镜'}],
        }

    def test_valid_handoff_is_not_quality_approval_and_does_not_write(self):
        before = copy.deepcopy(self.project)
        result = check_project(self.project, self.root, 'story')
        self.assertTrue(result['structure_passed'])
        self.assertFalse(result['quality_verified'])
        self.assertEqual(self.project, before)

    def test_changed_upstream_version_blocks_handoff(self):
        self.project['documents'][0]['version'] = 3
        self.assertFalse(check_project(self.project, self.root)['structure_passed'])

    def test_missing_output_blocks_handoff(self):
        (self.root / 'story.md').unlink()
        self.assertFalse(check_project(self.project, self.root)['structure_passed'])

    def test_outputs_cannot_escape_project(self):
        for path in ('../outside.md', str(self.root / 'story.md'), 'https://example.com/story.md'):
            with self.subTest(path=path):
                self.project['handoffs'][0]['outputs'] = [path]
                self.assertFalse(check_project(self.project, self.root)['structure_passed'])

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'story.md'
            target.write_text('external')
            (self.root / 'link.md').symlink_to(target)
            self.project['handoffs'][0]['outputs'] = ['link.md']
            self.assertFalse(check_project(self.project, self.root)['structure_passed'])

    def test_stage_requires_ready_handoff(self):
        self.assertFalse(check_project(self.project, self.root, 'production')['structure_passed'])

    def test_duplicate_ids_are_rejected(self):
        self.project['shots'].append({'shot_id': 'S1'})
        with self.assertRaises(ValueError):
            check_project(self.project, self.root)

    def test_wrong_selected_candidate_is_rejected(self):
        self.project['generations'] = [{'generation_id': 'G1', 'shot_id': 'S1'}]
        self.project['shots'][2]['selected_generation_id'] = 'G1'
        self.assertFalse(check_project(self.project, self.root)['structure_passed'])

    def test_context_selects_neighbours_and_identity_assets_without_history(self):
        self.project['generations'] = [{'generation_id': 'G1', 'shot_id': 'S2',
                                        'output_path': 'clip.mp4', 'prompt': 'private-prompt',
                                        'spec': {'image': 'https://private.example/image?token=secret'}},
                                       {'generation_id': 'G2', 'shot_id': 'S2'}]
        self.project['shots'][2]['selected_generation_id'] = 'G1'
        result = shot_context(self.project, 'S2')
        self.assertEqual([shot['shot_id'] for shot in result['shots']], ['S1', 'S2', 'S3'])
        self.assertEqual([asset['asset_id'] for asset in result['assets']], ['A1'])
        self.assertEqual([item['generation_id'] for item in result['generations']], ['G1'])
        self.assertNotIn('private-prompt', json.dumps(result))
        self.assertNotIn('token=secret', json.dumps(result))

    def test_missing_approved_identity_asset_is_rejected(self):
        self.project['assets'] = []
        self.assertFalse(check_project(self.project, self.root)['structure_passed'])

    def test_reference_case_requires_existing_project_analysis(self):
        self.project['reference_cases'] = [{'case_id': 'R1', 'analysis_path': 'missing.json',
                                            'related_shot_ids': ['S2']}]
        self.assertFalse(check_project(self.project, self.root)['structure_passed'])

    def test_unknown_shot_does_not_return_whole_project(self):
        with self.assertRaises(ValueError):
            shot_context(self.project, 'missing')


if __name__ == '__main__':
    unittest.main()
