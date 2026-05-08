import sys
import os
import subprocess

# --- 1. Python 3.13 補丁 ---
try:
    import audioop
except ImportError:
    import audioop_lts as audioop

    sys.modules["audioop"] = audioop

from pydub import AudioSegment

# --- 2. 設定工具路徑 ---
ffmpeg_dir = r"C:\icppython"
ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")

# 強制路徑注入
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
AudioSegment.converter = ffmpeg_exe
AudioSegment.ffprobe = ffprobe_exe


def ultimate_repair_and_split(file_path, num_segments=3):
    if not os.path.exists(file_path):
        print(f"❌ 錯誤：找不到音檔 {file_path}")
        return

    output_dir = os.path.dirname(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]

    # 建立一個絕對純淨的臨時 MP3
    temp_fixed_mp3 = os.path.join(output_dir, "pure_fixed.mp3")

    print(f"🚀 啟動終極修復程序...")
    print(f"第一階段：強制音訊數據重建 (此步驟最關鍵)...")

    # 使用 ffmpeg 強制重寫所有音訊流
    # -af "loudnorm" 會嘗試自動標準化音量（防止聲音太小被 AI 判斷為空檔）
    # -ar 44100 強制取樣率
    # -ac 1 強制轉為單聲道 (縮減體積且對 AI 最友善)
    repair_cmd = [
        ffmpeg_exe, "-y", "-i", file_path,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k",
        temp_fixed_mp3
    ]

    try:
        # 執行修復
        result = subprocess.run(repair_cmd, capture_output=True, text=True)

        if not os.path.exists(temp_fixed_mp3) or os.path.getsize(temp_fixed_mp3) < 1000:
            print("💥 致命錯誤：修復後的檔案大小異常，原始錄音可能完全沒有數據。")
            return

        print("✅ 數據重建完成！進入第二階段：精準切割...")

        # 讀取修好的檔案
        audio = AudioSegment.from_file(temp_fixed_mp3, format="mp3")
        total_ms = len(audio)
        segment_ms = total_ms // num_segments

        print(f"📢 偵測到有效長度：{total_ms / 1000 / 60:.2f} 分鐘")

        for i in range(num_segments):
            start_time = i * segment_ms
            end_time = (i + 1) * segment_ms if i < num_segments - 1 else total_ms

            chunk = audio[start_time:end_time]
            output_filename = os.path.join(output_dir, f"{base_name}_fixed_part_{i + 1}.mp3")

            print(f"正在導出第 {i + 1}/{num_segments} 段...")
            # 導出時再次確保標頭完整
            chunk.export(output_filename, format="mp3", bitrate="64k")
            print(
                f"   └─ 成功: {os.path.basename(output_filename)} ({os.path.getsize(output_filename) / 1024 / 1024:.2f} MB)")

        # 清理
        os.remove(temp_fixed_mp3)
        print(f"\n✨ 【重要】請在上傳前，先用電腦播放器打開其中一段聽聽看是否有聲音！")

    except Exception as e:
        print(f"💥 發生非預期錯誤: {e}")


if __name__ == "__main__":
    target_path = r"C:\icprecord\10.m4a"
    ultimate_repair_and_split(target_path, num_segments=3)