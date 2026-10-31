"""Eight-pad contact-driven melody, independent of the original three-pad demo.

Twinkle Twinkle Little Star is the traditional melody arranged here as six
phrases. Its rhythm is one beat per note, two beats at each phrase end.
"""
from __future__ import annotations
import argparse
import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
import pybullet as p
import pybullet_data
from PIL import Image, ImageDraw, ImageFont

HZ = 240
NOTES = ('C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5')
SOLFEGE = dict(zip(NOTES, ('Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si', 'Do+')))
FREQ = dict(zip(NOTES, (261.625565, 293.664768, 329.627557, 349.228231,
                        391.995436, 440.0, 493.883301, 523.251131)))
COLORS = dict(zip(NOTES, ((0.85,0.08,0.08,1), (0.95,0.35,0.05,1),
                           (0.88,0.75,0.04,1), (0.15,0.68,0.12,1),
                           (0.02,0.58,0.7,1), (0.1,0.25,0.85,1),
                           (0.55,0.14,0.77,1), (0.8,0.18,0.48,1))))
# Two rows of four. Centers are 15 cm apart; pads are 11 cm wide.
POSITIONS = {n:(x,y,0.055) for n,(x,y) in zip(NOTES,
    ((0.42,-0.225),(0.42,-0.075),(0.42,0.075),(0.42,0.225),
     (0.57,-0.225),(0.57,-0.075),(0.57,0.075),(0.57,0.225)))}
PHRASES = (
    ('C4','C4','G4','G4','A4','A4','G4'),
    ('F4','F4','E4','E4','D4','D4','C4'),
    ('G4','G4','F4','F4','E4','E4','D4'),
    ('G4','G4','F4','F4','E4','E4','D4'),
    ('C4','C4','G4','G4','A4','A4','G4'),
    ('F4','F4','E4','E4','D4','D4','C4'),
)


def make_score(piece):
    if piece == 'scale':
        return [{'note': note, 'beats': 1, 'phrase': 'scale'} for note in NOTES]
    if piece != 'twinkle':
        raise ValueError('Unknown piece')
    return [{'note': note, 'beats': 2 if i == len(phrase)-1 else 1,
             'phrase': phrase_index+1}
            for phrase_index, phrase in enumerate(PHRASES)
            for i,note in enumerate(phrase)]


def synthesize(contacts, duration, beat_seconds, path, rate=48000):
    samples = np.zeros(math.ceil(duration * rate), dtype=np.float64)
    for event in contacts:
        # Wrong-pad contacts also make the sound of the actual pad.
        beats = event.get('beats', 1)
        length = int(min(beat_seconds * beats * 0.88, duration) * rate)
        start = round(event['time_s'] * rate)
        end = min(len(samples), start + length)
        length = end-start
        if length <= 0:
            continue
        t = np.arange(length) / rate
        env = np.minimum(1, t / 0.012) * np.minimum(1, (length/rate-t) / 0.10)
        env *= np.exp(-t*0.5)
        f = FREQ[event['note']]
        tone = (np.sin(2*np.pi*f*t) + 0.22*np.sin(2*np.pi*2*f*t) +
                0.07*np.sin(2*np.pi*3*f*t)) / 1.29
        samples[start:end] += 0.30 * env * tone
    pcm = (np.clip(samples, -0.95, 0.95) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate)
        f.writeframes(pcm.tobytes())


def _font(size):
    for path in ('/System/Library/Fonts/Helvetica.ttc',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try: return ImageFont.truetype(path,size)
        except OSError: pass
    return ImageFont.load_default()


def render(width,height,client,active,piece):
    view=p.computeViewMatrix(cameraEyePosition=[1.18,-1.1,1.25],
                             cameraTargetPosition=[0.34,0,0.28],cameraUpVector=[0,0,1])
    projection=p.computeProjectionMatrixFOV(fov=55,aspect=width/height,nearVal=.05,farVal=5)
    rgba=p.getCameraImage(width,height,viewMatrix=view,projectionMatrix=projection,
                          renderer=p.ER_TINY_RENDERER,physicsClientId=client)[2]
    img=Image.fromarray(np.asarray(rgba,dtype=np.uint8).reshape(height,width,4)[:,:,:3])
    draw=ImageDraw.Draw(img,'RGBA'); sz=max(10,round(height*.034)); font=_font(sz)
    title=_font(max(12,round(height*.045))); margin=max(8,round(height*.025))
    draw.text((margin,margin), 'TWINKLE TWINKLE LITTLE STAR' if piece=='twinkle' else 'DO RE MI - PAD CHECK', font=title, fill=(30,45,65,255))
    y=margin+round(height*.065); line=max(sz+3,round(height*.042))
    for note in NOTES:
        rgb=tuple(round(x*255) for x in COLORS[note][:3]); selected=active == note
        draw.rectangle((margin,y+2,margin+line//2,y+line//2+2),fill=(*rgb,255),outline=(20,20,20,255))
        draw.text((margin+line*.7,y),f'{SOLFEGE[note]}  {note}'+('  *' if selected else ''),font=font,fill=(15,20,30,255))
        y+=line
    return np.asarray(img)


def run(score, piece, output, log, audio, fps=30, width=640, height=360):
    if fps <= 0 or HZ % fps or width < 64 or height < 64 or width%2 or height%2:
        raise ValueError('fps must divide 240; width/height must be even and >=64')
    output, log, audio = map(Path,(output,log,audio))
    if output.suffix.lower() != '.mp4' or audio.suffix.lower() != '.wav':
        raise ValueError('output must be MP4 and audio WAV')
    if len({output.resolve(),log.resolve(),audio.resolve()}) != 3:
        raise ValueError('output, audio and log must be distinct')
    for path in (output,log,audio): path.parent.mkdir(parents=True,exist_ok=True)
    if any(e.get('note') not in NOTES or e.get('beats') not in (1,2) for e in score):
        raise ValueError('Invalid score')
    # Four phase durations add to 1.6 seconds at 30 fps. All are rounded to
    # whole frames, keeping simulation and video clocks aligned for any fps.
    phase_seconds=(.6,.4,.2,.4)
    phase_frames=[max(1,round(s*fps)) for s in phase_seconds]
    beat_frames=sum(phase_frames); beat_seconds=beat_frames/fps
    steps_per_frame=HZ//fps
    client=p.connect(p.DIRECT)
    if client < 0: raise RuntimeError('Could not connect to PyBullet')
    writer=None; frames=0; steps=0; current=None; strikes=[]; contacts=[]
    touching={n:False for n in NOTES}; glow_until={n:-1 for n in NOTES}
    try:
        p.setAdditionalSearchPath(pybullet_data.getDataPath(),physicsClientId=client)
        p.setTimeStep(1/HZ,physicsClientId=client);p.setGravity(0,0,-9.81,physicsClientId=client)
        p.loadURDF('plane.urdf',physicsClientId=client)
        robot=p.loadURDF('kuka_iiwa/model.urdf',[0,0,0],useFixedBase=True,physicsClientId=client)
        col=p.createCollisionShape(p.GEOM_BOX,halfExtents=[.055,.055,.012],physicsClientId=client)
        pads={}
        for note in NOTES:
            vis=p.createVisualShape(p.GEOM_BOX,halfExtents=[.055,.055,.012],rgbaColor=COLORS[note],physicsClientId=client)
            pads[note]=p.createMultiBody(baseMass=0,baseCollisionShapeIndex=col,baseVisualShapeIndex=vis,
                                         basePosition=POSITIONS[note],physicsClientId=client)
        joints=[i for i in range(p.getNumJoints(robot,physicsClientId=client))
                if p.getJointInfo(robot,i,physicsClientId=client)[2]==p.JOINT_REVOLUTE]
        if len(joints)!=7: raise RuntimeError('Unexpected KUKA joint layout')
        ee=6; home=[.36,0,.65]
        with tempfile.TemporaryDirectory(prefix='robo-melody-') as tmp:
            silent=str(Path(tmp)/'silent.mp4')
            writer=imageio.get_writer(silent,fps=fps,codec='libx264',quality=7,macro_block_size=1)
            def move(goal,nframes):
                nonlocal frames,steps,current
                count=nframes*steps_per_frame
                start=np.array(p.getLinkState(robot,ee,computeForwardKinematics=True,physicsClientId=client)[4]);dest=np.array(goal)
                for n in range(count):
                    if steps%steps_per_frame==0:
                        for note,body in pads.items():
                            rgba=COLORS[note]
                            if steps < glow_until[note]: rgba=tuple(.65+.35*v for v in rgba[:3])+(1,)
                            p.changeVisualShape(body,-1,rgbaColor=rgba,physicsClientId=client)
                        active=(current['note'] if current and current['contact_confirmed'] and
                                steps < glow_until[current['note']] else None)
                        writer.append_data(render(width,height,client,active,piece));frames+=1
                    alpha=(n+1)/count; smooth=alpha*alpha*(3-2*alpha)
                    target=(start*(1-smooth)+dest*smooth).tolist()
                    qs=p.calculateInverseKinematics(robot,ee,target,maxNumIterations=100,residualThreshold=1e-4,physicsClientId=client)
                    for j,q in zip(joints,qs):
                        p.setJointMotorControl2(robot,j,p.POSITION_CONTROL,targetPosition=float(q),force=250,physicsClientId=client)
                    p.stepSimulation(physicsClientId=client);steps+=1
                    for note,body in pads.items():
                        points=p.getContactPoints(bodyA=robot,bodyB=body,linkIndexA=ee,physicsClientId=client)
                        points=[pt for pt in points if pt[9]>0]
                        now=bool(points)
                        if now and not touching[note]:
                            pt=max(points,key=lambda v:v[9])
                            event={'note':note,'time_s':steps/HZ,'robot_link':ee,'position_on_pad':list(pt[6]),
                                   'normal_force_n':float(pt[9]),'strike':current['strike'] if current else None,
                                   'intended_note':current['note'] if current else None,
                                   'beats':current['beats'] if current and current['note']==note else 1}
                            contacts.append(event);glow_until[note]=steps+round(.25*HZ)
                            if current and current['note']==note and not current['contact_confirmed']:
                                current.update(contact_confirmed=True,contact_time_s=steps/HZ,
                                               normal_force_n=event['normal_force_n'],position_on_pad=event['position_on_pad'])
                        touching[note]=now
            move(home,round(1.2*fps))
            for i,item in enumerate(score,1):
                note=item['note'];x,y,z=POSITIONS[note]
                current={'strike':i,'note':note,'beats':item['beats'],'phrase':item.get('phrase'),
                         'start_time_s':steps/HZ,'contact_confirmed':False,'contact_time_s':None,'normal_force_n':None}
                strikes.append(current)
                above=[x,y,z+.25]; hit=[x,y,z+.02]
                move(above,phase_frames[0]);move(hit,phase_frames[1]);move(hit,phase_frames[2]);move(above,phase_frames[3])
                for _ in range(item['beats']-1): move(above,beat_frames)
                current['end_time_s']=steps/HZ;current=None
            move(home,round(.6*fps))
            writer.close();writer=None
            if frames*steps_per_frame != steps: raise RuntimeError('video and physics clocks differ')
            duration=frames/fps
            synthesize(contacts,duration,beat_seconds,audio)
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-i',silent,'-i',str(audio),
                            '-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart','-shortest',str(output)],check=True)
        data={'piece':piece,'source':'hand-authored traditional melody' if piece=='twinkle' else 'scale check',
              'video':str(output),'audio':str(audio),'fps':fps,'width':width,'height':height,'duration_s':duration,
              'frame_count':frames,'simulation_hz':HZ,'nominal_beat_s':beat_seconds,'nominal_bpm':60/beat_seconds,
              'events':strikes,'contacts':contacts,'successful_strikes':sum(e['contact_confirmed'] for e in strikes),
              'total_strikes':len(strikes),
              'notes':['Sound is synthesized from actual force-bearing contact onsets, including unintended pads.',
                       'Pad glow is a color change; audio is not a physical impact sound.',
                       'Beat timing is nominal; actual contact onsets can differ due to robot movement.']}
        log.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        return data
    finally:
        if writer: writer.close()
        p.disconnect(physicsClientId=client)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--piece',choices=('scale','twinkle'),default='twinkle')
    parser.add_argument('--output',default='output/twinkle.mp4');parser.add_argument('--log',default='output/twinkle.json')
    parser.add_argument('--audio',default='output/twinkle.wav');parser.add_argument('--fps',type=int,default=30)
    parser.add_argument('--width',type=int,default=640);parser.add_argument('--height',type=int,default=360)
    args=parser.parse_args()
    r=run(make_score(args.piece),args.piece,args.output,args.log,args.audio,args.fps,args.width,args.height)
    print(f"{r['piece']}: {r['successful_strikes']}/{r['total_strikes']} contacts; {r['duration_s']:.2f}s; {r['nominal_bpm']:.2f} BPM")

if __name__=='__main__':main()
