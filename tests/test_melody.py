"""Score structure and actual eight-pad contact checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import melody


class MelodyTests(unittest.TestCase):
    def test_song_and_scale(self):
        score=melody.make_score('twinkle')
        self.assertEqual(len(score),42)
        self.assertEqual([e['note'] for e in score[:7]],list(('C4','C4','G4','G4','A4','A4','G4')))
        self.assertEqual([i for i,e in enumerate(score) if e['beats']==2],[6,13,20,27,34,41])
        self.assertEqual([e['note'] for e in melody.make_score('scale')],list(melody.NOTES))
        self.assertAlmostEqual(melody.FREQ['C5'],2*melody.FREQ['C4'],places=4)

    def test_no_contact_no_sound_and_two_beat_note_is_longer(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); a=tmp/'silent.wav';b=tmp/'long.wav'
            melody.synthesize([],4,1.0,a)
            melody.synthesize([{'note':'C4','time_s':.5,'beats':2}],4,1.0,b)
            with wave.open(str(a),'rb') as f: silent=np.frombuffer(f.readframes(f.getnframes()),'<i2')
            with wave.open(str(b),'rb') as f: sound=np.frombuffer(f.readframes(f.getnframes()),'<i2')
            self.assertFalse(np.any(silent));self.assertFalse(np.any(sound[:24000]))
            self.assertGreater(np.max(np.abs(sound[48000:96000])),0)

    def test_all_eight_pads_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            r=melody.run(melody.make_score('scale'),'scale',tmp/'scale.mp4',tmp/'events.json',tmp/'audio.wav',
                         fps=15,width=160,height=90)
            self.assertEqual(r['successful_strikes'],8)
            self.assertEqual([e['note'] for e in r['contacts']],list(melody.NOTES))
            self.assertTrue(all(c['intended_note']==c['note'] and c['normal_force_n']>0 for c in r['contacts']))
            self.assertEqual(r['frame_count']/r['fps'],r['duration_s'])
            self.assertEqual(json.loads((tmp/'events.json').read_text())['successful_strikes'],8)
            self.assertGreater((tmp/'scale.mp4').stat().st_size,0)

if __name__=='__main__': unittest.main()
