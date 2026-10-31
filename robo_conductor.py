"""ROBO CONDUCTOR: LLM-planned drum-pad tapping in PyBullet (Colab compatible)."""
import os, json, math, argparse
from pathlib import Path
import numpy as np
import pybullet as p
import pybullet_data
import imageio.v2 as imageio

COLORS = ('red', 'blue', 'green')
PAD_POS = {'red': (0.48, -0.24, 0.055), 'blue': (0.54, 0.0, 0.055), 'green': (0.48, 0.24, 0.055)}
RGB = {'red': (0.9, 0.12, 0.1, 1), 'blue': (0.1, 0.3, 0.9, 1), 'green': (0.1, 0.75, 0.2, 1)}


def make_plan(instruction, model='gpt-4.1-mini'):
    """Calls an actual LLM. Requires OPENAI_API_KEY; no simulated AI fallback."""
    from openai import OpenAI
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('OPENAI_API_KEY is missing. Set it in Colab Secrets or environment.')
    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={'type': 'json_object'},
        messages=[
            {'role': 'system', 'content': 'You are a robot percussion planner. Return only JSON of the form {"sequence":["red","blue"]}. Allowed values: red, blue, green. Translate Japanese color names 赤=red 青=blue 緑=green. Respect order and repetition. 1 to 12 strikes. No other keys.'},
            {'role': 'user', 'content': instruction},
        ],
    )
    raw = json.loads(response.choices[0].message.content)
    sequence = raw.get('sequence')
    if not isinstance(sequence, list) or not 1 <= len(sequence) <= 12 or any(c not in COLORS for c in sequence):
        raise ValueError(f'Invalid AI plan: {raw}')
    return {'instruction': instruction, 'sequence': sequence, 'model': model, 'source': 'OpenAI API'}


def create_pad(position, rgba):
    half = [0.085, 0.085, 0.012]
    col = p.createCollisionShape(p.GEOM_BOX, halfExtents=half)
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=half, rgbaColor=rgba)
    return p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col, baseVisualShapeIndex=vis,
                             basePosition=position)


def camera(width, height):
    view = p.computeViewMatrix(cameraEyePosition=[1.15, -1.05, 1.12],
                               cameraTargetPosition=[0.27, 0, 0.38], cameraUpVector=[0, 0, 1])
    proj = p.computeProjectionMatrixFOV(fov=57, aspect=width/height, nearVal=0.05, farVal=5)
    result = p.getCameraImage(width, height, viewMatrix=view, projectionMatrix=proj,
                              renderer=p.ER_TINY_RENDERER)
    return np.asarray(result[2], dtype=np.uint8).reshape(height, width, 4)[:, :, :3].copy()


def simulate(plan, output='robot_demo.mp4', fps=24, width=960, height=540):
    p.connect(p.DIRECT)
    try:
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        p.setTimeStep(1/240)
        p.loadURDF('plane.urdf')
        robot = p.loadURDF('kuka_iiwa/model.urdf', [0, 0, 0], useFixedBase=True)
        for color in COLORS:
            create_pad(PAD_POS[color], RGB[color])
        # The KUKA iiwa URDF's last link index is 6.
        ee_link = 6
        joint_ids = [j for j in range(p.getNumJoints(robot)) if p.getJointInfo(robot, j)[2] == p.JOINT_REVOLUTE]
        if len(joint_ids) != 7:
            raise RuntimeError('Unexpected KUKA joint layout')
        writer = imageio.get_writer(output, fps=fps, codec='libx264', quality=7, macro_block_size=16)
        frames = 0
        events = []
        sim_steps_per_frame = 10
        home = [0.36, 0, 0.65]

        def move(target, seconds):
            nonlocal frames
            n = max(1, int(seconds * fps))
            start = np.asarray(p.getLinkState(robot, ee_link, computeForwardKinematics=True)[4])
            goal = np.asarray(target)
            for i in range(n):
                alpha = (i + 1) / n
                smooth = alpha * alpha * (3 - 2 * alpha)
                xyz = (start * (1-smooth) + goal * smooth).tolist()
                joints = p.calculateInverseKinematics(robot, ee_link, xyz,
                                                      maxNumIterations=100, residualThreshold=1e-4)
                for j, q in zip(joint_ids, joints):
                    p.setJointMotorControl2(robot, j, p.POSITION_CONTROL,
                                            targetPosition=float(q), force=250)
                for _ in range(sim_steps_per_frame):
                    p.stepSimulation()
                writer.append_data(camera(width, height))
                frames += 1

        # Settle to an initial raised pose.
        move(home, 1.0)
        for idx, color in enumerate(plan['sequence'], 1):
            x, y, z = PAD_POS[color]
            # Approach above the pad, then lower to near the surface, then retreat.
            above = [x, y, z + 0.25]
            contact = [x, y, z + 0.10]
            move(above, 0.65)
            move(contact, 0.35)
            actual = p.getLinkState(robot, ee_link, computeForwardKinematics=True)[4]
            error = float(np.linalg.norm(np.asarray(actual) - np.asarray(contact)))
            events.append({'strike': idx, 'color': color, 'target_xyz': contact,
                           'actual_xyz': list(actual), 'position_error_m': round(error, 4),
                           'video_time_s': round(frames / fps, 2)})
            move(above, 0.35)
        move(home, 0.8)
        writer.close()
        return {'video': output, 'duration_s': round(frames / fps, 2), 'events': events,
                'note': 'This demo uses end-effector proximity to a pad, not verified contact force.'}
    finally:
        p.disconnect()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instruction', default='赤、青、緑、赤の順番で叩いて')
    parser.add_argument('--output', default='robot_demo.mp4')
    parser.add_argument('--model', default='gpt-4.1-mini')
    args = parser.parse_args()
    plan = make_plan(args.instruction, args.model)
    Path('plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    print('AI plan:', plan)
    result = simulate(plan, args.output)
    Path('results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Result:', json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
