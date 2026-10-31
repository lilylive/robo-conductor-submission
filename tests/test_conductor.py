"""Checks of provenance, sound timing, and a real three-pad simulation."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conductor


class ConductorTest(unittest.TestCase):
    def test_patterns_and_provenance(self):
        strikes, source = conductor.make_strikes('all', None)
        self.assertEqual(len(set(tuple(v) for v in conductor.PATTERNS.values())), 3)
        self.assertEqual({x['pattern'] for x in strikes}, set(conductor.PATTERNS))
        self.assertEqual(source['type'], 'manual')
        with self.assertRaises(ValueError):
            conductor.validate_plan({'sequence': ['red', 'purple']})

    def test_audio_is_driven_by_confirmed_contact(self):
        events = [{'color': 'red', 'contact_confirmed': False, 'contact_time_s': None},
                  {'color': 'blue', 'contact_confirmed': True, 'contact_time_s': 0.5}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sound.wav'
            conductor.synthesize(events, 1.0, path)
            with wave.open(str(path), 'rb') as sound:
                data = np.frombuffer(sound.readframes(sound.getnframes()), dtype='<i2')
                self.assertEqual(sound.getframerate(), 48000)
            self.assertEqual(np.max(np.abs(data[:24000])), 0)
            self.assertGreater(np.max(np.abs(data[24000:30000])), 0)

    def test_actual_three_pad_contacts_and_video_time(self):
        strikes = [{'color': c, 'pattern': 'test'} for c in ('red', 'red', 'blue', 'green')]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            result = conductor.run(strikes, {'type': 'test'}, tmp/'demo.mp4', tmp/'events.json',
                                   tmp/'sound.wav', fps=15, width=160, height=90)
            self.assertEqual(result['frame_count'] / result['fps'], result['duration_s'])
            self.assertEqual(result['successful_strikes'], 4)
            self.assertTrue(all(e['normal_force_n'] > 0 for e in result['events']))
            self.assertTrue(all(0 < e['contact_time_s'] < result['duration_s'] for e in result['events']))
            self.assertEqual(json.loads((tmp/'events.json').read_text())['successful_strikes'], 4)
            self.assertGreater((tmp/'demo.mp4').stat().st_size, 0)


if __name__ == '__main__':
    unittest.main()
