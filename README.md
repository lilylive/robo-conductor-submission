# ROBO CONDUCTOR

ROBO CONDUCTORは、ロボットアームが色のついたパッドに触れて演奏する、Physical AI応用1講座の最終課題です。私は、自然言語による演奏計画と、ドから高いドまでの音階を使った演奏を組み合わせ、ロボットの動きを音と映像で表現する作品を制作しました。ロボットにはPyBullet上のKUKA iiwaを使用し、対象パッドとの物理シミュレーション上の接触に応じて、パッドの色を変え、音を生成します。制作には生成AIによる支援も活用しました。

## 対話版：自然言語で順番に指示する

新しい対話版では、文字で入力した指示をOpenAI APIで解釈し、色の順番や登録曲「きらきら星」を演奏します。演奏後に次の指示を入力できます。

## AIの利用と演奏の関係

`robo_conductor.py` はOpenAI APIを使い、自然言語の指示を赤・青・緑の演奏順序に変換します。`examples/plan.json` には「赤、青、緑、赤」の計画がOpenAI API由来として記録され、`examples/results.json` と `examples/robot_demo.mp4` にはその計画を使った実行記録があります。APIの利用元については保存済みファイルの記載に基づいており、今回のMacでの検証では新たなAPI呼び出しを行っていません。

「きらきら星」の音符は**あらかじめコードに記述した固定の譜面**です。

## 作品の構成

- `robo_conductor.py`：AI計画生成と3色パッドへの接近を行う基礎プログラム。接近を記録し、接触力は判定しません。
- `conductor.py`：3色の手動パターンまたは保存済み計画を使い、接触・色変化・音声・映像を記録する改良版。
- `melody.py`：8音のパッドで、きらきら星を約37.5 BPM・約78.6秒で演奏する版。
- `melody_50bpm.py`：同じ曲を約50 BPM・約59.4秒で演奏する版。単独では課題の動画要件である1分に届きません。
- `notebooks/ROBO_CONDUCTOR_きらきら星_Colab.ipynb`：きらきら星のColab用ノートブック。旧ノートブックは原本として別途保存しています。
- `examples/`：3色版の計画・ログ・映像と、各演奏版の検証ログ。
- `docs/`：検証記録など。最新のレポートは別途PDFにして提出します。
- `tests/`：計画、音声、物理シミュレーションを確認するテスト。


## 動作環境と準備

macOS Apple Silicon、Python 3.11.15で検証しました。公式版PyBullet 3.2.7はこのMac上でソースビルドが失敗したため、Apple Siliconでは別途保守されているフォーク `pybullet-arm64` 3.2.8を使いました。両配布物は同じ `pybullet` モジュールを提供するため、同一環境への重複インストールは避けてください。[PyBullet本体](https://github.com/bulletphysics/bullet3)／[Apple Silicon対応フォーク](https://github.com/tomsilver/pybullet-arm64)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` はApple Siliconでフォーク、それ以外で公式版を選びます。PythonやOSの組み合わせによっては、公式版のビルドが必要になったり、失敗したりする場合があります。Colabでは後述のノートブックの手順を使ってください。

## きらきら星を再生する

以下は1〜3分の要件に入る約78.6秒の演奏です。映像、接触ログ、音声を `output/` に保存します。既存の同名ファイルは上書きされるため、必要な場合は出力先を変更してください。

```bash
python melody.py --piece twinkle --fps 30 --width 640 --height 360 \
  --output output/twinkle.mp4 --log output/twinkle.json --audio output/twinkle.wav
```

`--width 1920 --height 1080` でフルHDを指定できます。CPU描画のため時間がかかります。音階を順に確かめるときは `--piece scale` を指定します。約59.4秒の速めの版は `melody_50bpm.py` で生成できますが、提出動画にする場合は説明などを追加して1分以上にしてください。詳しくは [8音版の説明](README_きらきら星.md) を参照してください。

## Google Colabで実行する

`notebooks/ROBO_CONDUCTOR_きらきら星_Colab.ipynb` をColabにアップロードし、セルを上から実行します。音階・きらきら星と出力解像度を選び、生成した動画・音声・ログを保存できます。ノートブックはコードを内包するため、通常の曲の演奏に別のZIPやAPIキーは必要ありません。任意のAI計画には、保存済み計画の再生と、新規API呼び出しの選択肢があります。MacのJupyterでは通常の曲と保存済み計画を検証しましたが、Colab本番と新規API呼び出しは未確認です。

`notebooks/ROBO_CONDUCTOR_Colab.ipynb` は3色版のノートブックです。このノートブックには `robo_conductor.py` を書き出すセルがあり、同名ファイルがある作業フォルダで実行すると上書きされるため注意してください。

## 3色版とAI計画を再生する

手動パターンを連続再生する場合：

```bash
python conductor.py --output output/three_patterns.mp4 --log output/three_patterns.json --audio output/three_patterns.wav
```

保存済みのAI計画を使う場合：

```bash
python conductor.py --plan examples/plan.json --output output/ai_plan.mp4 --log output/ai_plan.json --audio output/ai_plan.wav
```

この再生ではAPIを呼び出しません。計画ファイルに記載された由来を記録しますが、ファイルの記載だけで生成元を独立に認証するものではありません。

新しい自然言語の計画を作る場合のみ、OpenAI APIキーと通信・利用料金が必要です。キーは環境変数で設定し、ファイルやノートブック、公開リポジトリには記載しないでください。元コードは実行したフォルダの `plan.json`、`results.json`、動画を上書きするため注意してください。

```bash
export OPENAI_API_KEY='ご自身のAPIキー'
python robo_conductor.py --instruction '赤、青、緑、赤の順番で叩いて'
```

