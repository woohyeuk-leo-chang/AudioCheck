import os
import csv
import difflib
import argparse
import re


def find_audio_path(base_dir, pid, filename):
    """
    Locates a trial's audio file. The experiment stores the path it saved to
    (e.g. "data/1/audio/..." or "data_seq\\1\\audio\\block_1\\set_1\\trial_1.wav"),
    which breaks once the data folder is renamed or moved, so the part after
    the participant folder is also tried under base_dir/pid.
    """
    if not isinstance(filename, str) or not filename.strip():
        return None
    # Normalize separators
    filename = filename.replace('\\', '/')
    pid = str(pid)

    candidates = []

    # 1. As absolute path or relative to current working directory
    candidates.append(filename)

    # 2. Relative to the participant directory inside base_dir
    # e.g. base_dir/1/audio/trial_1.wav when filename is "audio/trial_1.wav"
    candidates.append(os.path.join(base_dir, pid, filename))

    # 3. Whatever came before the participant folder ("data/1/", "data_seq/1/",
    #    an old absolute path...), re-rooted at base_dir/pid
    parts = filename.split('/')
    if pid in parts[:-1]:
        cut = parts.index(pid)
        candidates.append(os.path.join(base_dir, pid, *parts[cut + 1:]))

    # Check all candidates (files only -- an empty name must not match the folder)
    for c in candidates:
        if os.path.isfile(c):
            return c

    return None


def transcribe_and_compare(participant_id, data_dir="data", status_callback=None):
    """
    Reads data csv for a participant, finds audio files, transcribes them, 
    and compares with the target phrase.
    
    Args:
        participant_id: ID of the participant.
        data_dir: Root data directory.
        status_callback: Optional function (msg) -> None to report progress.
    """
    
    def log(msg):
        print(msg)
        if status_callback:
            status_callback(msg)

    # Construct paths
    participant_data_dir = os.path.join(data_dir, str(participant_id))
    csv_filename = f"{participant_id}_data.csv"
    csv_path = os.path.join(participant_data_dir, csv_filename)
    
    if not os.path.exists(csv_path):
        log(f"Error: CSV file not found at {csv_path}")
        return False

    # Output file
    output_csv_filename = f"{participant_id}_transcription_results.csv"
    output_csv_path = os.path.join(participant_data_dir, output_csv_filename)

    import shutil
    
    # Check for FFMPEG dependency
    if not shutil.which("ffmpeg"):
        import platform
        system_os = platform.system()
        
        error_msg = "Error: FFMPEG is not installed or not in PATH. Whisper requires FFMPEG to process audio."
        log(error_msg)
        
        if system_os == "Darwin": # macOS
            log("Please install FFMPEG: 'brew install ffmpeg'")
        elif system_os == "Windows":
            log("Please install FFMPEG: Open PowerShell and run 'winget install ffmpeg'")
        else:
            log("Please install FFMPEG from https://ffmpeg.org/download.html")
            
        return False

    # Initialize Whisper Model
    log("Loading Whisper model (base)... This may take a moment on first run.")
    try:
        import whisper
        # Load model once
        model = whisper.load_model("base")
    except ImportError:
        log("Error: 'openai-whisper' not installed. Please install it via pip.")
        return False
    except Exception as e:
        log(f"Error loading Whisper model: {e}")
        return False

    results = []

    log(f"Processing participant {participant_id}...")
    log(f"Reading from: {csv_path}")

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            total_rows = len(rows)

            for i, row in enumerate(rows):
                audio_rel_path = row.get('audio_filename', '').replace('\\', '/') # Fix windows paths
                target_phrase = row.get('phrase', '')
                block = row.get('block', '')
                mini_block = row.get('set', '')  # ADP2: trial numbers restart in every mini-block
                trial = row.get('trial', '')

                audio_file_path = find_audio_path(data_dir, participant_id, audio_rel_path)
                
                if not audio_file_path:
                    # Fallback to original for error reporting
                    audio_file_path = audio_rel_path
                
                transcribed_text = ""
                similarity_score = 0.0
                error_msg = ""
                
                log(f"[{i+1}/{total_rows}] Block {block}, Set {mini_block}, Trial {trial}: {audio_file_path}")

                if os.path.exists(audio_file_path):
                    try:
                        # Transcribe with Whisper
                        # fp16=False prevents warnings on CPU (mps/cuda autofallback handled by whisper usually)
                        result = model.transcribe(audio_file_path, 
                                                  initial_prompt=target_phrase,
                                                  fp16=False)
                        # Normalize: lower case and keep ONLY alphanumeric + spaces (regex)
                        # This handles unicode punctuation (curly quotes etc) by exclusion
                        raw_text = result["text"].lower()
                        transcribed_text = re.sub(r'[^\w\s]', '', raw_text).strip()
                        log(f"    -> Transcribed: '{transcribed_text}'")
                    except Exception as e:
                        error_msg = f"Error processing audio file: {e}"
                        log(f"    -> Error: {error_msg}")
                else:
                    error_msg = "Audio file not found"
                    log(f"    -> Error: {error_msg}")

                # Comparison Logic
                if transcribed_text and target_phrase:
                    # Normalize texts (lowercase, strip, remove punctuation if needed)
                    t1 = transcribed_text.lower().strip()
                    t2 = target_phrase.lower().strip()
                    similarity_score = difflib.SequenceMatcher(None, t1, t2).ratio()
                
                results.append({
                    'block': block,
                    'set': mini_block,
                    'trial': trial,
                    'audio_filename': audio_rel_path,
                    'target_phrase': target_phrase,
                    'transcribed_text': transcribed_text,
                    'similarity_score': similarity_score,
                    'error': error_msg
                })

    except Exception as e:
        log(f"Critical Error reading CSV: {e}")
        return False

    # Write results
    if results:
        fieldnames = ['block', 'set', 'trial', 'audio_filename', 'target_phrase', 'transcribed_text', 'similarity_score', 'error']
        try:
            with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            log(f"Done! Results saved to: {output_csv_path}")
            return True
        except Exception as e:
            log(f"Error writing output CSV: {e}")
            return False
    else:
        log("No results to save.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio files and compare with target text.")
    parser.add_argument("participant_id", help="The ID of the participant (folder name in data directory)")
    parser.add_argument("--data-dir", default="data", help="Folder holding the participant folders (e.g. data_seq)")
    
    # Check if arguments are passed, if not prompt user
    if len(os.sys.argv) == 1:
        # Interactive mode
        p_id = input("Enter Participant ID: ").strip()
        transcribe_and_compare(p_id)
    else:
        args = parser.parse_args()
        transcribe_and_compare(args.participant_id, data_dir=args.data_dir)
