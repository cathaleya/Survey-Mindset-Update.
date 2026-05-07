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
        nidn = st.text_input("NIDN / NIP")
        unit = st.text_input("Unit Kerja / Fakultas / Bagian")
        jabatan = st.selectbox("Jabatan", ["Dosen", "Tenaga Kependidikan (Tendik)"])
        
        submit_bio = st.form_submit_button("Mulai Survei")
        
        if submit_bio:
            if nama and nidn and unit:
                st.session_state.user_data = {
                    "Nama": nama,
                    "NIDN": nidn,
                    "Unit_Kerja": unit,
                    "Jabatan": jabatan,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.page = "survey"
                st.rerun()
            else:
                st.warning("Mohon lengkapi semua field biodata.")

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
            
        submit_survey = st.form_submit_button("Simpan & Lihat Ringkasan 🏁")
        
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
                st.session_state.page = "summary"
                st.rerun()
            else:
                st.error("Mohon jawab semua pernyataan sebelum mengirim.")

# --- PAGE: SUMMARY ---
elif st.session_state.page == "summary":
    import plotly.express as px
    import plotly.graph_objects as go

    # Layout Header: Judul dan Tombol Kirim
    col_t, col_b = st.columns([2, 1])
    with col_t:
        st.title("✅ Ringkasan & Analisis Hasil")
        st.write(f"Halo, **{st.session_state.user_data['Nama']}**! Berikut adalah ringkasan capaian Anda.")
    
    # Calculate scores (needed before button and metrics)
    total_score = 0
    cat_scores = {"Mindset": 0, "Culture": 0}
    cat_counts = {"Mindset": 0, "Culture": 0}
    response_dist = {"Sangat Setuju": 0, "Setuju": 0, "Tidak Setuju": 0, "Sangat Tidak Setuju": 0}
    
    final_responses = {}
    for k, v in st.session_state.user_data.items():
        final_responses[k] = v
        
    for q in questions:
        ans = st.session_state.answers.get(str(q["id"]))
        if ans:
            score = ans["score"]
            text = ans["text"]
            total_score += score
            cat_scores[q["category"]] += score
            cat_counts[q["category"]] += 1
            response_dist[text] += 1
            
            final_responses[f"Q{q['id']}"] = text
            final_responses[f"Score{q['id']}"] = score

    final_responses["Total_Score"] = total_score
    max_score = len(questions) * 4
    percentage = (total_score / max_score) * 100

    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Kirim Hasil Sekarang", use_container_width=True):
            with st.spinner("Sedang mengirim..."):
                if save_via_apps_script(final_responses):
                    st.success("Berhasil Terkirim!")
                    st.session_state.page = "finish"
                    st.rerun()
                else:
                    st.error("Gagal mengirim.")
    
    st.markdown("---")

    # Display Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Skor", f"{total_score} / {max_score}")
    col2.metric("Persentase", f"{percentage:.1f}%")
    
    # Interpretation
    status = ""
    color = ""
    if percentage >= 80:
        status = "Sangat Baik (Sangat Berorientasi Pelayanan)"
        color = "green"
    elif percentage >= 60:
        status = "Baik (Berorientasi Pelayanan)"
        color = "blue"
    elif percentage >= 40:
        status = "Cukup (Perlu Sedikit Peningkatan)"
        color = "orange"
    else:
        status = "Kurang (Perlu Pengembangan Intensif)"
        color = "red"
    
    col3.markdown(f"**Status:** <span style='color:{color}'>{status}</span>", unsafe_allow_html=True)

    st.markdown("---")
    
    # CHARTS SECTION
    st.subheader("📊 Analisis Statistik")
    
    tab1, tab2 = st.tabs(["Capaian Per Dimensi", "Distribusi Jawaban"])
    
    with tab1:
        # Calculate percentage per category
        cat_data = []
        for cat in cat_scores:
            cat_max = cat_counts[cat] * 4
            cat_perc = (cat_scores[cat] / cat_max) * 100
            cat_data.append({"Kategori": cat, "Persentase": cat_perc})
        
        df_cat = pd.DataFrame(cat_data)
        fig_cat = px.bar(df_cat, x="Kategori", y="Persentase", 
                         title="Persentase Capaian Mindset vs Culture",
                         text=df_cat['Persentase'].apply(lambda x: '{0:1.1f}%'.format(x)),
                         color="Kategori",
                         color_discrete_sequence=["#1f77b4", "#ff7f0e"])
        fig_cat.update_yaxes(range=[0, 100])
        st.plotly_chart(fig_cat, use_container_width=True)

    with tab2:
        df_dist = pd.DataFrame(list(response_dist.items()), columns=['Jawaban', 'Jumlah'])
        fig_dist = px.pie(df_dist, values='Jumlah', names='Jawaban', 
                          title="Distribusi Pilihan Jawaban",
                          color_discrete_sequence=px.colors.sequential.RdBu_r)
        st.plotly_chart(fig_dist, use_container_width=True)

    st.markdown("---")
    
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
