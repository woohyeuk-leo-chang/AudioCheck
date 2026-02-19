import streamlit as st
import pandas as pd
import os
import glob
import difflib
import threading
import time
import signal
import streamlit.components.v1 as components
from audiocheck_transcriber import transcribe_and_compare

# --- Keyboard Shortcuts Logic ---
def inject_keyboard_shortcuts():
    # This JS runs in the parent window to capture global key events
    shortcuts_js = """
    <script>
    const doc = window.parent.document;
    
    // Use a flag to prevent multiple listeners if script re-runs
    if (!window.parent._shortcuts_initialized) {
        doc.addEventListener('keydown', function(e) {
            // Ignore if user is typing in an input or textarea
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
                return;
            }

            if (e.key === 'ArrowLeft') {
                const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('Previous'));
                if (btn) btn.click();
            } else if (e.key === 'ArrowRight') {
                const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('Next'));
                if (btn) btn.click();
            } else if (e.altKey && (e.code === 'KeyC' || e.key === 'c' || e.key === 'C')) {
                const labels = Array.from(doc.querySelectorAll('label'));
                const target = labels.find(el => el.innerText.includes('Mark as Correct'));
                if (target) target.click();
            } else if (e.altKey && (e.code === 'KeyR' || e.key === 'r' || e.key === 'R')) {
                const labels = Array.from(doc.querySelectorAll('label'));
                const target = labels.find(el => el.innerText.includes('Mark as Reviewed'));
                if (target) target.click();
            }
        });
        window.parent._shortcuts_initialized = true;
    }
    </script>
    """
    components.html(shortcuts_js, height=0)

# --- Automatic Shutdown Logic ---
# This stops the server when no browser tabs are active
def monitor_sessions():
    time.sleep(10) # Initial grace period for startup
    while True:
        try:
            from streamlit.runtime import get_instance
            rt = get_instance()
            if rt:
                sessions = rt._session_mgr.list_active_sessions()
                if len(sessions) == 0:
                    # Grace period for refreshes/switching tabs
                    time.sleep(15) 
                    sessions = rt._session_mgr.list_active_sessions()
                    if len(sessions) == 0:
                        os.kill(os.getpid(), signal.SIGINT)
        except Exception:
            pass
        time.sleep(10)

if "monitor_thread_started" not in st.session_state:
    # Use a global-ish check to avoid multiple threads across reruns
    if not any(t.name == "ShutdownMonitor" for t in threading.enumerate()):
        threading.Thread(target=monitor_sessions, name="ShutdownMonitor", daemon=True).start()
    st.session_state.monitor_thread_started = True

# Set page title and layout
st.set_page_config(page_title="AudioCheck", layout="wide")

# Initialize Keyboard Shortcuts
inject_keyboard_shortcuts()

def get_participants(data_dir="data"):
    if not os.path.exists(data_dir):
        return []
    # Find folders that look like participant IDs (digits)
    return sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d)) and d.isdigit()])

def load_data(participant_id, data_dir="data"):
    p_dir = os.path.join(data_dir, str(participant_id))
    csv_path = os.path.join(p_dir, f"{participant_id}_transcription_results.csv")
    
    if not os.path.exists(csv_path):
        return None, None

    df = pd.read_csv(csv_path)
    
    # Ensure manual_correct column exists
    if 'manual_correct' not in df.columns:
        df['manual_correct'] = False
    
    # Ensure manual_correct is boolean
    df['manual_correct'] = df['manual_correct'].fillna(False).astype(bool)

    # Ensure manual_reviewed column exists
    if 'manual_reviewed' not in df.columns:
        df['manual_reviewed'] = False
    
    # Ensure manual_reviewed is boolean
    df['manual_reviewed'] = df['manual_reviewed'].fillna(False).astype(bool)

    # Ensure original_transcription column exists (for change tracking)
    if 'original_transcription' not in df.columns:
        df['original_transcription'] = df['transcribed_text']

    return df, csv_path

def save_data(df, path):
    df.to_csv(path, index=False)
    # Silent save or subtle toast
    st.toast(f"Saved changes to {os.path.basename(path)}", icon="💾")

# --- Sidebar ---
st.sidebar.title("AudioCheck")

# Data Directory Logic
# Priority: 1. Session State (if set and valid) -> 2. ./data -> 3. ../data
found_data_dir = None

possible_dirs = ["data", "../data", "../Adp1/data", "../ADP1/data"]
for d in possible_dirs:
    if os.path.exists(d) and os.path.isdir(d):
        found_data_dir = d
        break

if not found_data_dir:
    st.error("### ⚠️ Data Folder Not Found")
    st.markdown("""
    **Please follow these steps:**
    1. Create a folder named `data` in the same directory as this tool.
    2. Place your participant folders (e.g., `101`, `102`) inside that `data` folder.
    3. Click the button below to reload.
    """)
    if st.button("🔄 Retry / Reload"):
        st.rerun()
    st.stop()

# Set the valid data dir
st.session_state.data_dir = found_data_dir
    
# Participant Selection
participants = get_participants(st.session_state.data_dir)
if not participants:
    st.sidebar.warning(f"No participant folders found in `{st.session_state.data_dir}`.")
    st.stop()

selected_pid = st.sidebar.selectbox("Select Participant", participants)

# --- Transcription Handling ---
p_dir = os.path.join(st.session_state.data_dir, str(selected_pid))
results_csv = os.path.join(p_dir, f"{selected_pid}_transcription_results.csv")
data_exists = os.path.exists(results_csv)

if not data_exists:
    st.sidebar.warning(f"No transcriptions found for {selected_pid}.")
    if st.sidebar.button("Run Transcription Now"):
        with st.spinner(f"Transcribing audio for Participant {selected_pid}... (This may take a while)"):
            # Progress container
            log_container = st.sidebar.empty()
            def update_status(msg):
                log_container.text(msg)
            
            # Pass the custom data directory
            success = transcribe_and_compare(selected_pid, data_dir=st.session_state.data_dir, status_callback=update_status)
            
            if success:
                st.sidebar.success("Transcription complete!")
                st.rerun()
            else:
                st.sidebar.error("Transcription failed. Check console for details.")
    st.stop() # Process stops here if no data

# Optional: Re-run transcription even if data exists
st.sidebar.markdown("---")
if st.sidebar.button("Re-run Transcription"):
    with st.spinner(f"Re-transcribing Participant {selected_pid}..."):
        log_container = st.sidebar.empty()
        def update_status(msg):
            log_container.text(msg)
        success = transcribe_and_compare(selected_pid, data_dir=st.session_state.data_dir, status_callback=update_status)
        if success:
            st.sidebar.success("Done!")
            st.rerun()

# --- Load Data & Review Interface ---
# Reload if PID changes or data not in state
if 'data' not in st.session_state or st.session_state.get('current_pid') != selected_pid:
    df, csv_path = load_data(selected_pid, data_dir=st.session_state.data_dir)
    if df is not None:
        st.session_state.data = df
        st.session_state.csv_path = csv_path
        st.session_state.current_pid = selected_pid
    else:
        st.error("Error loading data.")
        st.stop()

# Re-fetch from state in case of updates
df = st.session_state.data
csv_path = st.session_state.csv_path

# Filters
st.sidebar.markdown("---")
st.sidebar.subheader("Review Controls")
show_low_conf = st.sidebar.checkbox("Filter by Similarity Score", value=True)
hide_reviewed = st.sidebar.checkbox("Hide Reviewed Trials", value=False)
sort_priority = st.sidebar.checkbox("Sort: Unreviewed First", value=True)


# Filter logic
mask = pd.Series(True, index=df.index)
if show_low_conf:
    threshold = st.sidebar.slider("Confidence Threshold", 0.0, 1.0, 1.0, 0.05)
    # Important: Let corrected/reviewed items stay even if they now have high scores
    mask &= (df['similarity_score'] < threshold) | (df['manual_correct']) | (df['manual_reviewed'])

if hide_reviewed:
    # Explicitly remove finished items if requested
    mask &= (~df['manual_reviewed'])

filtered_df = df[mask].copy()

# Navigation List & Sorting
def get_trial_label(row):
    # Icons: 🔵 = Corrected, ✅ = Reviewed, ⚠️ = Low confidence, ✔️ = High confidence
    if row.get('manual_reviewed'):
        status = "✅"
    elif row.get('manual_correct'):
        status = "🔵"
    else:
        status = "⚠️" if row['similarity_score'] < 0.8 else "✔️"
    return f"{status} B{row['block']} T{row['trial']} ({row['similarity_score']:.2f})"

# Sorting Logic
if sort_priority:
    # Unreviewed first (manual_reviewed=0), then Block/Trial
    filtered_df['sort_reviewed'] = filtered_df['manual_reviewed'].astype(int)
    filtered_indices = filtered_df.sort_values(['sort_reviewed', 'block', 'trial']).index.tolist()
else:
    # Natural order (Block/Trial)
    filtered_indices = filtered_df.sort_values(['block', 'trial']).index.tolist()

st.sidebar.write(f"Showing {len(filtered_indices)} / {len(df)} trials")

if not filtered_indices:
    st.info("No trials match the current filters.")
    st.markdown("### Data Preview (All Trials)")
    st.dataframe(df, use_container_width=True)
    st.stop()

# --- Selection Logic with Persistence ---
if 'current_trial_idx' not in st.session_state or st.session_state.current_trial_idx not in filtered_indices:
    st.session_state.current_trial_idx = filtered_indices[0]

# Sidebar Navigation Buttons
col_prev, col_next = st.sidebar.columns(2)
curr_pos = filtered_indices.index(st.session_state.current_trial_idx)

# Sync the selectbox key with the current_trial_idx before rendering
st.session_state.temp_selectbox = st.session_state.current_trial_idx

if col_prev.button("⬅️ Previous", use_container_width=True, disabled=(curr_pos == 0)):
    st.session_state.current_trial_idx = filtered_indices[curr_pos - 1]
    st.rerun()

if col_next.button("Next ➡️", use_container_width=True, disabled=(curr_pos == len(filtered_indices) - 1)):
    st.session_state.current_trial_idx = filtered_indices[curr_pos + 1]
    st.rerun()

def on_selectbox_change():
    st.session_state.current_trial_idx = st.session_state.temp_selectbox

# Removed 'index' because it's now handled by the state sync above
selected_index = st.sidebar.selectbox(
    "Select Trial", 
    filtered_indices, 
    format_func=lambda i: get_trial_label(df.loc[i]),
    key="temp_selectbox",
    on_change=on_selectbox_change
)

# --- Main Content ---
row = df.loc[selected_index]

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(f"Block {row['block']}, Trial {row['trial']}")
with col2:
    val = row['similarity_score']
    color = "normal" if val == 1.0 else ("inverse" if val < 0.8 else "off")
    st.metric("Similarity", f"{val:.2f}", delta_color=color)

# Comparison Card
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Target Phrase**")
    st.info(f"### {row['target_phrase']}")

with c2:
    st.markdown("**Transcribed Text**")
    
    # Check if we have a valid string, handle NaN
    current_text = row['transcribed_text']
    original_text = row.get('original_transcription', current_text) # Fallback if missing
    
    if pd.isna(current_text):
        current_text = ""
    if pd.isna(original_text):
        original_text = ""
        
    def update_transcription():
        new_text = st.session_state[f"transcribe_{selected_index}"]
        target = row['target_phrase']
        
        # Calculate new similarity
        if new_text and target:
            t1 = new_text.lower().strip()
            t2 = target.lower().strip()
            new_score = difflib.SequenceMatcher(None, t1, t2).ratio()
        else:
            new_score = 0.0
            
        # Update session state dataframe
        st.session_state.data.at[selected_index, 'transcribed_text'] = new_text
        st.session_state.data.at[selected_index, 'similarity_score'] = new_score
        
        # Autosave
        save_data(st.session_state.data, st.session_state.csv_path)
        
    # Text Input for manual editing
    st.text_input(
        "Edit Transcription",
        value=current_text,
        key=f"transcribe_{selected_index}",
        on_change=update_transcription,
        label_visibility="collapsed"
    )

    def update_correct():
        st.session_state.data.at[selected_index, 'manual_correct'] = st.session_state[f"correct_{selected_index}"]
        save_data(st.session_state.data, st.session_state.csv_path)

    def update_reviewed():
        new_val = st.session_state[f"reviewed_{selected_index}"]
        st.session_state.data.at[selected_index, 'manual_reviewed'] = new_val
        save_data(st.session_state.data, st.session_state.csv_path)
        
        # Auto-advance logic: Find the next NOT-YET-REVIEWED trial in the queue
        if new_val:
            try:
                curr_idx_in_queue = filtered_indices.index(selected_index)
                next_unreviewed = None
                for i in range(curr_idx_in_queue + 1, len(filtered_indices)):
                    candidate_id = filtered_indices[i]
                    if not st.session_state.data.at[candidate_id, 'manual_reviewed']:
                        next_unreviewed = candidate_id
                        break
                if next_unreviewed is not None:
                    st.session_state.current_trial_idx = next_unreviewed
            except (ValueError, IndexError):
                pass

    col_btn_1, col_btn_2 = st.columns(2)
    with col_btn_1:
        st.checkbox(
            "Mark as Correct (🔵)", 
            value=bool(row['manual_correct']),
            key=f"correct_{selected_index}",
            on_change=update_correct,
            help="Indicates the transcription is accurate (Alt + C)"
        )
    with col_btn_2:
        st.checkbox(
            "Mark as Reviewed (✅)", 
            value=bool(row['manual_reviewed']),
            key=f"reviewed_{selected_index}",
            on_change=update_reviewed,
            help="Mark this trial finished and move to next (Alt + R)"
        )
    
    # Show change tracking if modified
    if str(current_text) != str(original_text):
        st.caption(f"Original: *{original_text}*")



# Audio Player
st.markdown("---")
audio_filename = row['audio_filename']

# Robust audio path finder
def find_audio_path(base_dir, pid, filename):
    # Normalize separators
    filename = filename.replace('\\', '/')
    
    candidates = []
    
    # 1. As absolute path or relative to current working directory
    candidates.append(filename)
    
    # 2. Relative to the participant directory inside base_dir
    # e.g. base_dir/1/audio/trial_1.wav
    # This works if filename is just "audio/trial_1.wav"
    candidates.append(os.path.join(base_dir, str(pid), filename))
    
    # 3. Handle case where filename includes "data/{pid}/" prefix
    if filename.startswith(f"data/{pid}/"):
        stripped = filename.replace(f"data/{pid}/", "", 1)
        candidates.append(os.path.join(base_dir, str(pid), stripped))
        
    # 4. Handle generic "data/" prefix if base_dir ends with "data"
    if filename.startswith("data/") and base_dir.rstrip('/').endswith("data"):
        parent = os.path.dirname(base_dir.rstrip('/'))
        candidates.append(os.path.join(parent, filename))

    # Check all candidates
    for c in candidates:
        if os.path.exists(c):
            return c
            
    return None

final_audio_path = find_audio_path(st.session_state.data_dir, selected_pid, audio_filename)

if final_audio_path:
    st.audio(final_audio_path)
else:
    st.error(f"Audio file not found: {audio_filename}")
    st.markdown(f"**Search Debug:**\n- Data Dir: `{st.session_state.data_dir}`\n- Participant: `{selected_pid}`\n- Path in CSV: `{audio_filename}`")


# Data Table Preview (Focused Window)
st.markdown("---")
st.markdown(f"### Data Preview (Focused)")

# Calculate a window around the selected index to ensure it's visible
try:
    curr_preview_pos = filtered_indices.index(selected_index)
    total_filtered = len(filtered_indices)
    window_size = 7
    
    if total_filtered <= window_size:
        window_indices = filtered_indices
    else:
        # Start with ideal centering (3 before, 3 after)
        start_win = curr_preview_pos - 3
        end_win = curr_preview_pos + 4
        
        # Adjust if hitting limits to maintain 7 rows
        if start_win < 0:
            start_win = 0
            end_win = window_size
        elif end_win > total_filtered:
            end_win = total_filtered
            start_win = total_filtered - window_size
            
        window_indices = filtered_indices[start_win:end_win]
except (ValueError, IndexError):
    window_indices = filtered_indices[:7] # Fallback

def highlight_selected(r):
    return ['background-color: rgba(64, 128, 255, 0.2)' if r.name == selected_index else '' for _ in r]

st.dataframe(
    df.loc[window_indices].style.apply(highlight_selected, axis=1),
    use_container_width=True,
    hide_index=False
)

# Full Data View
st.markdown("---")
with st.expander("📂 View Full Dataset (All Trials)"):
    st.dataframe(df, use_container_width=True)

# Sidebar Footer (at the very bottom)
st.sidebar.markdown("---")
with st.sidebar.expander("⌨️ Keyboard Shortcuts"):
    st.markdown("""
    - **← (Left Arrow)**: Previous Trial
    - **→ (Right Arrow)**: Next Trial
    - **Alt + C**: Toggle 'Mark as Correct'
    - **Alt + R**: Toggle 'Mark as Reviewed'
    - **Enter**: (While editing) Save & Stay
    """)

if st.sidebar.button("🛑 Shut Down Server", help="Click here to completely stop the application and close the terminal."):
    st.sidebar.warning("Shutting down... You can close this tab now.")
    time.sleep(1)
    os.kill(os.getpid(), signal.SIGINT)

