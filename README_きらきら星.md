# 8音パッドで「きらきら星」を演奏する

ド（C4）から高いド（C5）まで8つのパッドを並べ、ロボットアームで主旋律を演奏する機能を制作しました。パッドの色と音名は動画左側の凡例で確認できます。曲の音符はコード内にあらかじめ固定されており、演奏時にAIが譜面を生成するわけではありません。自然言語からのAI計画は3色版に別途あります。システム全体とAI利用の説明は [README](README.md) を参照してください。

## 動画の長さを選ぶ

`melody.py` は約37.5 BPM、約78.6秒の全曲版です。講座が指定する1〜3分の範囲に入り、ロボットの演奏部分だけで1分以上になります。`melody_50bpm.py` は約50 BPM、約59.4秒です。こちらは単独では1分に満たないため、提出には説明などを加えてください。どちらも色の変化・合成音・接触ログを含みます。

## 実行

[README](README.md) の環境準備後、次を実行します。作業用の標準画質で約78.6秒の動画、WAV、JSONを生成します。

```bash
python melody.py --piece twinkle --width 640 --height 360 --fps 30 \
  --output output/twinkle.mp4 --log output/twinkle.json --audio output/twinkle.wav
```

フルHDは `--width 1920 --height 1080` を指定します。描画には時間がかかります。音階の確認は `--piece scale`、約59.4秒の速めの版は `python melody_50bpm.py` を使います。同名の出力は上書きされます。

Google Colabでは、`notebooks/ROBO_CONDUCTOR_きらきら星_Colab.ipynb` をアップロードして上から実行してください。ノートブックはコードを内包し、通常の曲の演奏と保存済みAI計画の再生にはAPIキーは必要ありません。新規にAI計画を作る場合はAPIキーと通信が必要で、料金が発生する場合があります。Colab本番での実行は未確認です。



旋律の参考楽譜：[MakingMusicFun.net](https://www.makingmusicfun.net/htm/f_printit_free_printable_sheet_music/twinkle-twinkle-little-star-beginner-piano)
