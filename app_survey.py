import streamlit as st
import json
import pandas as pd
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
        nama = st.text_input("Nama Lengkap")
        nim = st.text_input("NIM / ID Mahasiswa")
        univ = st.text_input("Universitas")
        semester = st.selectbox("Semester", ["1", "2", "3", "4", "5", "6", "7", "8", ">8"])
        
        submit_bio = st.form_submit_button("Mulai Survei")
        
        if submit_bio:
            if nama and nim and univ:
                st.session_state.user_data = {
                    "Nama": nama,
                    "NIM": nim,
                    "Universitas": univ,
                    "Semester": semester,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.page = 1
                st.rerun()
            else:
                st.warning("Mohon lengkapi semua field biodata.")

# --- PAGE: QUESTIONNAIRE ---
elif isinstance(st.session_state.page, int):
    q_idx = st.session_state.page - 1
    q = questions[q_idx]
    
    st.title(f"Pernyataan {st.session_state.page} dari {len(questions)}")
    st.progress(st.session_state.page / len(questions))
    
    st.subheader("Pernyataan:")
    st.write(q["scenario"])
    
    st.markdown("---")
    st.subheader("Pilihan Tindakan:")
    
    current_ans = st.session_state.answers.get(str(q["id"]), None)
    choice = st.radio(
        "Pilih jawaban yang paling sesuai:",
        options=[opt["text"] for opt in q["options"]],
        index=None if current_ans is None else [opt["text"] for opt in q["options"]].index(current_ans["text"])
    )
    
    col1, col2 = st.columns([1,1])
    with col1:
        if st.session_state.page > 1:
            if st.button("⬅️ Kembali"):
                st.session_state.page -= 1
                st.rerun()
    with col2:
        if st.button("Lanjut ➡️" if st.session_state.page < len(questions) else "Ringkasan 🏁"):
            if choice:
                selected_opt = next(opt for opt in q["options"] if opt["text"] == choice)
                st.session_state.answers[str(q["id"])] = {
                    "text": choice,
                    "score": selected_opt["score"]
                }
                if st.session_state.page < len(questions):
                    st.session_state.page += 1
                else:
                    st.session_state.page = "summary"
                st.rerun()
            else:
                st.warning("Pilih salah satu jawaban.")

# --- PAGE: SUMMARY ---
elif st.session_state.page == "summary":
    st.title("✅ Ringkasan Jawaban")
    st.write(f"Terima kasih, **{st.session_state.user_data['Nama']}**!")
    
    total_score = 0
    final_responses = {}
    for k, v in st.session_state.user_data.items():
        final_responses[k] = v
        
    summary_list = []
    for q in questions:
        ans = st.session_state.answers.get(str(q["id"]))
        total_score += ans["score"] if ans else 0
        final_responses[f"Q{q['id']}"] = ans["text"] if ans else ""
        final_responses[f"Score{q['id']}"] = ans["score"] if ans else 0
        summary_list.append({"No": q["id"], "Skor": ans["score"] if ans else 0})

    final_responses["Total_Score"] = total_score
    st.metric("Total Skor", f"{total_score} / {len(questions) * 4}")
    
    if st.button("🚀 Kirim Hasil Sekarang"):
        with st.spinner("Sedang mengirim..."):
            if save_via_apps_script(final_responses):
                st.success("Berhasil! Data Anda sudah masuk ke Google Sheets Peneliti.")
                st.balloons()
                st.session_state.page = "finish"
            else:
                st.error("Pengiriman otomatis gagal.")
                st.info("Silakan copy data berikut dan kirim ke Peneliti:")
                st.code(json.dumps(final_responses, indent=2))

# --- PAGE: FINISH ---
elif st.session_state.page == "finish":
    st.title("🏁 Selesai")
    st.success("Jawaban Anda telah tersimpan.")
    if st.button("Mulai Baru"):
        st.session_state.clear()
        st.rerun()
