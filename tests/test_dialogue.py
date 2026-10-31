"""AI応答はスタブ化し、課金APIへの通信は行わない。"""
import json
import os
import sys
import tempfile
import traceback
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dialogue


def reply(payload, *, refusal=None, finish="stop"):
    content = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,
        message=SimpleNamespace(content=content, refusal=refusal))])


def client_for(*responses):
    calls = []
    queue = iter(responses)
    def create(**kwargs):
        calls.append(kwargs)
        return next(queue)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    client.calls = calls
    return client


COLORS = {"action":"colors", "colors":["red","blue","green","red"], "song":"none", "reason":"指定色を順に叩く"}
SONG = {"action":"song", "colors":[], "song":"twinkle", "reason":"きらきら星"}
UNKNOWN = {"action":"unsupported", "colors":[], "song":"none", "reason":"未登録の曲"}


class DialogueTests(unittest.TestCase):
    def test_two_successive_ai_responses_and_visible_pad_colors(self):
        client = client_for(reply(COLORS), reply(SONG))
        first = dialogue.interpret_instruction('赤、青、緑、赤の順番で叩いて', client=client)
        self.assertEqual([s['note'] for s in dialogue.score_from_plan(first)], ['C4', 'A4', 'F4', 'C4'])
        second = dialogue.interpret_instruction('きらきら星を弾いて', client=client)
        score = dialogue.score_from_plan(second)
        self.assertEqual(len(score), 42)
        self.assertEqual([s['note'] for s in score[:7]], ['C4','C4','G4','G4','A4','A4','G4'])
        self.assertEqual([s['beats'] for s in score[:7]], [1,1,1,1,1,1,2])
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]['messages'][1]['content'], '赤、青、緑、赤の順番で叩いて')
        self.assertTrue(client.calls[0]['response_format']['json_schema']['strict'])
        self.assertEqual(client.calls[1]['messages'][1]['content'], 'きらきら星を弾いて')

    def test_unknown_refusal_incomplete_and_malformed(self):
        unknown = dialogue.interpret_instruction('別の曲を弾いて', client=client_for(reply(UNKNOWN)))
        with self.assertRaises(dialogue.PlanError): dialogue.score_from_plan(unknown)
        with self.assertRaises(dialogue.AIRequestError):
            dialogue.interpret_instruction('赤', client=client_for(reply('{}', refusal='refused')))
        with self.assertRaises(dialogue.AIRequestError):
            dialogue.interpret_instruction('赤', client=client_for(reply('{}', finish='length')))
        with self.assertRaises(dialogue.AIRequestError):
            dialogue.interpret_instruction('赤', client=client_for(reply('{bad')))
        with self.assertRaises(dialogue.PlanError):
            dialogue.interpret_instruction('赤', client=client_for(reply({'action':'colors','colors':['purple'],'song':'none','reason':''})))
        with self.assertRaises(dialogue.PlanError):
            dialogue.validate_plan({'action':'song','colors':['red'],'song':'twinkle','reason':''})
        with self.assertRaises(dialogue.PlanError):
            dialogue.validate_plan({**COLORS,'program':'print(1)'})
        with self.assertRaises(dialogue.PlanError):
            dialogue.validate_plan({**COLORS,'colors':['red']*13})

    def test_missing_key_and_network_error_no_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(dialogue.AIRequestError, 'OPENAI_API_KEY'):
                dialogue.interpret_instruction('きらきら星を弾いて')
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: (_ for _ in ()).throw(RuntimeError('do-not-expose-secret')))))
        with self.assertRaises(dialogue.AIRequestError) as err:
            dialogue.interpret_instruction('赤を叩いて', client=client)
        self.assertNotIn('do-not-expose-secret', str(err.exception))
        self.assertNotIn('do-not-expose-secret', ''.join(traceback.format_exception(err.exception)))

    def test_first_instruction_and_next_song_in_physics(self):
        # OpenAIの応答だけをスタブ化し、2つの譜面は実際のPyBulletで順番に演奏する。
        client = client_for(reply(COLORS), reply(SONG))
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            first = dialogue.interpret_instruction('赤、青、緑、赤の順番で叩いて', client=client)
            a = dialogue.perform_plan(first, tmp/'one.mp4', tmp/'one.json', tmp/'one.wav', fps=15, width=160, height=90)
            self.assertEqual(a['successful_strikes'], 4)
            self.assertEqual([e['note'] for e in a['events']], ['C4','A4','F4','C4'])
            self.assertEqual(len(a['contacts']), 4)
            self.assertTrue(all(e['note'] == e['intended_note'] for e in a['contacts']))
            second = dialogue.interpret_instruction('きらきら星を弾いて', client=client)
            b = dialogue.perform_plan(second, tmp/'two.mp4', tmp/'two.json', tmp/'two.wav', fps=15, width=160, height=90)
            self.assertEqual(b['successful_strikes'], 42)
            self.assertEqual(len(b['contacts']), 42)
            self.assertTrue(all(e['note'] == e['intended_note'] for e in b['contacts']))
            self.assertEqual(b['duration_s'], 78.6)
            self.assertEqual(json.loads((tmp/'one.json').read_text())['interpreted_plan'], first)
            self.assertEqual(json.loads((tmp/'two.json').read_text())['interpreted_plan'], second)
            self.assertTrue(all((tmp/(str(n)+ext)).stat().st_size > 0 for n in ('one','two') for ext in ('.mp4','.wav','.json')))


if __name__ == '__main__': unittest.main()
