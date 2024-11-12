# ベースイメージとしてPython 3.9を使用
FROM python:3.11

# 作業ディレクトリを設定
WORKDIR /app

# requirements.txtをコンテナにコピー
COPY requirements.txt .

# requirements.txtを使用して必要なパッケージをインストール
RUN pip install -r requirements.txt

# 必要なPythonスクリプトをコンテナにコピー
COPY . .

# デフォルトのコマンドを設定
CMD ["python", "main.py"]