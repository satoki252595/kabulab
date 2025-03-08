#!/usr/bin/env bash
set -e

# ----------------------------------
# 0. 下準備
# ----------------------------------
mkdir -p output

# 1) ユーザに複数URLを入力させる
urls=()
echo "=== Enter YouTube URLs (one per line)."
echo "=== Leave empty and press Enter when done. ==="
while true; do
  read -r -p "URL> " url
  if [ -z "$url" ]; then
    break
  fi
  urls+=("$url")
done

if [ ${#urls[@]} -eq 0 ]; then
  echo "[ERROR] No URLs were provided. Exiting."
  exit 1
fi

# 2) 言語の選択
echo "Select Language Code:"
echo "  1) ja   (Japanese)"
echo "  2) en   (English)"
echo "  3) auto (Auto-detect by Whisper)"
read -rp "Enter the number [1-3]: " lang_choice

case "$lang_choice" in
  1)  LANGUAGE="ja" ;;
  2)  LANGUAGE="en" ;;
  3)  # autoの場合、敢えて whisper に --language 引数を渡さない
      LANGUAGE="auto"
      ;;
  *)  
      echo "[INFO] Invalid choice. Use default: ja"
      LANGUAGE="ja"
      ;;
esac

# 3) モデルの選択
echo "Select Whisper Model:"
echo "  1) tiny"
echo "  2) base"
echo "  3) small"
echo "  4) medium"
echo "  5) large"
read -rp "Enter the number [1-5]: " model_choice

case "$model_choice" in
  1)  MODEL="tiny" ;;
  2)  MODEL="base" ;;
  3)  MODEL="small" ;;
  4)  MODEL="medium" ;;
  5)  MODEL="large" ;;
  *)
      echo "[INFO] Invalid choice. Use default: medium"
      MODEL="medium"
      ;;
esac

# Whisper に渡す言語引数を組み立て
# auto選択時は --language オプションを付与しない → Whisperが自動検出
LANG_ARG=()
if [ "$LANGUAGE" != "auto" ]; then
  LANG_ARG=(--language "$LANGUAGE")
fi

echo "=== Start Transcription for All URLs ==="
echo

# ----------------------------------
# 4. URLごとのダウンロード＆文字起こし
# ----------------------------------
for url in "${urls[@]}"; do
  echo "---------------------------------------"
  echo "Processing: $url"

  # yt-dlpでダウンロード時のファイル名を取得
  #   %(title)s  : 動画タイトル
  #   %(ext)s    : 拡張子
  FILE_NAME=$(yt-dlp --get-filename -o "%(title)s.%(ext)s" "$url")

  echo "[Download] => $FILE_NAME"
  yt-dlp -o "%(title)s.%(ext)s" "$url"

  echo "[Transcribe] => $FILE_NAME"
  # Whisperコマンド:
  #   --output_dir output : 出力ファイルを最初から ./output に置く
  #   --output_format txt : テキストファイルのみ生成
  whisper "$FILE_NAME" \
    --model "$MODEL" \
    --output_dir output \
    --output_format txt \
    "${LANG_ARG[@]}"

  # 生成ファイル例:
  #   output/タイトル.mp4.txt
  #   あるいは output/タイトル.mp4.ja.txt (言語指定されている場合)
  #   あるいは output/タイトル.mp4.en.txt (auto判定で英語と判断された場合)
  # …などの可能性がある

  # ここで、最終的なファイル名を「タイトル.txt」にそろえるならリネームする
  # ただし Whisper は「タイトル.mp4.ja.txt」等を出力する可能性あり
  # => 一意に特定するためワイルドカードで探す
  base_no_ext="${FILE_NAME%.*}"               # タイトル (拡張子除去, ex: MyVideoTitle.mp4 -> MyVideoTitle)
  pattern="output/${base_no_ext}*.txt"        # 例: "output/MyVideoTitle.mp4*.txt"
  candidate_txts=( $pattern )

  if [ ${#candidate_txts[@]} -eq 0 ]; then
    echo "[WARN] No transcription .txt found for $FILE_NAME"
  else
    # もし複数あった場合は先頭を採用
    local_txt="${candidate_txts[0]}"
    # 例: local_txt="output/MyVideoTitle.mp4.en.txt"

    # 拡張子をもう1段落として最終的に "MyVideoTitle.txt" にしたければ:
    #   MyVideoTitle.mp4.en.txt -> MyVideoTitle.txt
    final_txt="output/${base_no_ext%.*}.txt"
    mv "$local_txt" "$final_txt"
    
    # 他に同名系ファイルがあれば削除 (余計なものは不要)
    for f in "${candidate_txts[@]:1}"; do
      rm -f "$f"
    done

    echo "Created => $final_txt"
  fi

  # ダウンロードした動画ファイルは削除
  rm -f "$FILE_NAME"
done

echo "---------------------------------------"
echo "=== Done! All transcriptions are in the 'output' folder. ==="