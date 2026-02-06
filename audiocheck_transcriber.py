import os
import csv
import difflib
import argparse
import re


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
                trial = row.get('trial', '')

                # Audio file path construction
                audio_file_path = audio_rel_path
                
                transcribed_text = ""
                similarity_score = 0.0
                error_msg = ""
                
                log(f"[{i+1}/{total_rows}] Block {block}, Trial {trial}: {audio_file_path}")

                if os.path.exists(audio_file_path):
                    try:
                        # Transcribe with Whisper
                        # fp16=False prevents warnings on CPU (mps/cuda autofallback handled by whisper usually)
                        result = model.transcribe(audio_file_path, fp16=False)
                        # Normalize: lower case and keep ONLY alphanumeric + spaces (regex)
                        # This handles unicode punctuation (curly quotes etc) by exclusion
                        raw_text = result["text"].lower()
                        transcribed_text = re.sub(r'[^\w\s]', '', raw_text)
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
        fieldnames = ['block', 'trial', 'audio_filename', 'target_phrase', 'transcribed_text', 'similarity_score', 'error']
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
    
    # Check if arguments are passed, if not prompt user
    if len(os.sys.argv) == 1:
        # Interactive mode
        p_id = input("Enter Participant ID: ").strip()
        transcribe_and_compare(p_id)
    else:
        args = parser.parse_args()
        transcribe_and_compare(args.participant_id)
