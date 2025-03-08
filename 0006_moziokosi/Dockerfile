# ベースイメージには Python を利用します
FROM python:3.9-slim

# Whisperが動作するために ffmpeg が必要なのでインストール
RUN apt-get update && apt-get install -y ffmpeg bash \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの作成
WORKDIR /app

# requirements.txt をコピーしてインストール
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Whisperをインストール
# (PyPIからインストール: openai-whisper)
RUN pip install --no-cache-dir openai-whisper

# エントリーポイントスクリプトをコピー
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# 起動時に実行されるスクリプトを指定
ENTRYPOINT ["/app/entrypoint.sh"]