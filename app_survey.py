import streamlit as st
import json
import requests
import os
from datetime import datetime

# Set Page Config
st.set_page_config(page_title="Survei Mindset dan Culture-Set Berorientasi Pelayanan", layout="centered")

# Get absolute path of the current directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_PATH = os.path.join(CURRENT_DIR, "questions.json")

# Load Questions
if not os.path.exists(QUESTIONS_PATH):
    st.error(f"File '{QUESTIONS_PATH}' tidak ditemukan. Pastikan file pertanyaan sudah diunggah.")
    st.stop()

with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
    questions = json.load(f)

# Initialize Session State
if "page" not in st.session_state:
    st.session_state.page = "biodata"
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

# Helper Function to Save via Apps Script
def save_via_apps_script(data):
    try:
        url = None
        # Cek beberapa kemungkinan struktur secrets
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        elif "gsheets_url" in st.secrets:
            url = st.secrets["gsheets_url"]
        elif "spreadsheet" in st.secrets:
            url = st.secrets["spreadsheet"]

        if url:
            # Detect if it's an Apps Script URL
            if "script.google.com" in url:
                response = requests.post(url, json=data)
                if response.status_code == 200:
                    return True
                else:
                    st.error(f"Error dari Apps Script (Status {response.status_code}): {response.text}")
                    return False
            else:
                st.error("URL yang dimasukkan bukan URL Google Apps Script yang valid.")
                return False
        else:
            st.error("Konfigurasi URL tidak ditemukan di Secrets Streamlit Cloud.")
            st.info("Pastikan Anda sudah menambahkan [connections.gsheets] spreadsheet = 'URL' di bagian Secrets.")
            return False
    except Exception as e:
        st.error(f"Gagal koneksi ke server: {e}")
        return False

# --- PAGE: BIODATA ---
if st.session_state.page == "biodata":
    st.title("📋 Biodata Peserta")
    st.info("Silakan lengkapi data diri Anda sebelum memulai survei.")
    
    with st.form("form_biodata"):
        unit = st.text_input("Unit Kerja / Fakultas / Bagian")
        jabatan = st.selectbox("Jabatan", ["Dosen", "Tenaga Kependidikan (Tendik)"])
        
        submit_bio = st.form_submit_button("Mulai Survei")
        
        if submit_bio:
            if unit:
                st.session_state.user_data = {
                    "Unit_Kerja": unit,
                    "Jabatan": jabatan,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.page = "survey"
                st.rerun()
            else:
                st.warning("Mohon lengkapi data unit kerja.")

# --- PAGE: QUESTIONNAIRE ---
elif st.session_state.page == "survey":
    st.title("📋 Kuisioner Survei")
    st.markdown("### Mindset dan Culture-Set Berorientasi Pelayanan")
    st.info("Pilihlah jawaban yang paling mencerminkan kondisi atau sikap Anda sehari-hari.")
    
    # Define options for later reference
    likert_options = ["Sangat Setuju", "Setuju", "Tidak Setuju", "Sangat Tidak Setuju"]
    
    with st.form("form_survey"):
        # Group questions by category
        categories = ["Mindset", "Culture"]
        for cat in categories:
            st.subheader(f"Bagian: {cat} Berorientasi Pelayanan")
            cat_questions = [q for q in questions if q.get("category") == cat]
            
            for q in cat_questions:
                st.write(f"**{q['id']}. {q['scenario']}**")
                # Pre-select answer if already answered
                current_val = st.session_state.answers.get(str(q["id"]), {}).get("text", None)
                idx = likert_options.index(current_val) if current_val in likert_options else None
                
                st.radio(
                    f"Respon untuk Q{q['id']}",
                    options=likert_options,
                    index=idx,
                    key=f"q_{q['id']}",
                    horizontal=True,
                    label_visibility="collapsed"
                )
                st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            
        submit_survey = st.form_submit_button("Kirim Jawaban Sekarang 🏁")
        
        if submit_survey:
            # Validate all questions are answered
            all_answered = True
            temp_answers = {}
            for q in questions:
                ans_text = st.session_state[f"q_{q['id']}"]
                if ans_text:
                    # Find score from options in questions.json
                    score = next(opt["score"] for opt in q["options"] if opt["text"] == ans_text)
                    temp_answers[str(q["id"])] = {
                        "text": ans_text,
                        "score": score
                    }
                else:
                    all_answered = False
                    break
            
            if all_answered:
                st.session_state.answers = temp_answers
                
                # Build final responses for sending
                total_score = 0
                final_responses = {}
                for k, v in st.session_state.user_data.items():
                    final_responses[k] = v
                    
                for q in questions:
                    ans = temp_answers.get(str(q["id"]))
                    if ans:
                        score = ans["score"]
                        text = ans["text"]
                        total_score += score
                        final_responses[f"Q{q['id']}"] = text
                        final_responses[f"Score{q['id']}"] = score

                final_responses["Total_Score"] = total_score
                
                with st.spinner("Sedang mengirim jawaban..."):
                    if save_via_apps_script(final_responses):
                        st.session_state.page = "finish"
                        st.rerun()
                    else:
                        st.error("Gagal mengirim jawaban. Mohon periksa koneksi internet Anda.")
            else:
                st.error("Mohon jawab semua pernyataan sebelum mengirim.")

# --- PAGE: FINISH ---
elif st.session_state.page == "finish":
    st.balloons()
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: red; font-size: 50px;'>Terima kasih sudah mengisi survey</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.success("Jawaban Anda telah tersimpan di database peneliti.")
    
    if st.button("Mulai Baru"):
        st.session_state.clear()
        st.rerun()
