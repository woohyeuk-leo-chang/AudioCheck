
import streamlit as st
import pandas as pd
import os
import glob
import difflib
from audiocheck_transcriber import transcribe_and_compare

# Set page title and layout
st.set_page_config(page_title="AudioCheck", layout="wide")

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

possible_dirs = ["data", "../data"]
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
st.sidebar.subheader("Review Filters")
show_low_conf = st.sidebar.checkbox("Filter by Similarity Score", value=True)

if show_low_conf:
    threshold = st.sidebar.slider("Confidence Threshold", 0.0, 1.0, 0.8, 0.05)
    # Logic: Show trials where similarity < threshold
    filtered_df = df[df['similarity_score'] < threshold]
    st.sidebar.caption(f"Showing trials with similarity < {threshold}")
else:
    filtered_df = df

st.sidebar.write(f"Showing {len(filtered_df)} / {len(df)} trials")

# Navigation List
def get_trial_label(row):
    status = "✅" if row.get('manual_correct') else ("⚠️" if row['similarity_score'] < 0.8 else "✔️")
    return f"{status} Block {row['block']}, Trial {row['trial']} ({row['similarity_score']:.2f})"

filtered_indices = filtered_df.index.tolist()

if not filtered_indices:
    st.info("No trials match the current filters.")
    # Show full data preview anyway
    st.markdown("### Data Preview (All Trials)")
    st.dataframe(df, use_container_width=True)
    st.stop()

# Use index for selection using a unique key based on filter state to avoid errors
selected_index = st.sidebar.selectbox(
    "Select Trial", 
    filtered_indices, 
    format_func=lambda i: get_trial_label(df.loc[i]),
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
    
    # Show change tracking if modified
    if str(current_text) != str(original_text):
        st.caption(f"Original: *{original_text}*")


# Audio Player
st.markdown("---")
audio_path = row['audio_filename']
full_audio_path = os.path.join(st.session_state.data_dir, str(selected_pid), audio_path) if os.path.basename(audio_path) == audio_path else audio_path

# Try relative to Data Dir first, then direct path
if not os.path.exists(audio_path):
    # Try constructing path assuming audio is inside participant folder
    possible_path = os.path.join(st.session_state.data_dir, str(selected_pid), audio_path)
    if os.path.exists(possible_path):
        audio_path = possible_path

if os.path.exists(audio_path):
    st.audio(audio_path)
else:
    # Try fixing path separators if on windows/mac mix
    audio_path = audio_path.replace('\\', '/')
    possible_path = os.path.join(st.session_state.data_dir, str(selected_pid), audio_path)
    
    if os.path.exists(audio_path):
        st.audio(audio_path)
    elif os.path.exists(possible_path):
        st.audio(possible_path)
    else:
        st.error(f"Audio file not found: {audio_path}")

# Actions
st.markdown("---")
st.markdown("### Verification")

def update_correct():
    # Toggle the value in the dataframe
    new_val = st.session_state[f"correct_{selected_index}"]
    st.session_state.data.at[selected_index, 'manual_correct'] = new_val
    # Autosave
    save_data(st.session_state.data, st.session_state.csv_path)

is_correct = st.checkbox(
    "Mark as Correct (Override Similarity Score)", 
    value=bool(row['manual_correct']),
    key=f"correct_{selected_index}",
    on_change=update_correct
)

# Data Table Preview
st.markdown("---")
st.markdown("### Data Preview")
def highlight_selected(r):
    return ['background-color: rgba(128, 128, 128, 0.3)' if r.name == selected_index else '' for _ in r]

st.dataframe(
    df.loc[filtered_indices].style.apply(highlight_selected, axis=1),
    use_container_width=True,
    height=300
)

# Full Data View
st.markdown("---")
with st.expander("📂 View Full Dataset (All Trials)"):
    st.dataframe(df, use_container_width=True)

