import streamlit as st
import os
import asyncio
import edge_tts
import base64
from io import BytesIO
import zipfile
import tempfile
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Leitor de Texto com edge-tts", page_icon="💬", layout="centered")

# CSS fixo, funcional e seguro
st.markdown("""

<style>
    body, .stApp {
        background-color: #f1fce1 !important;
        color: #1D3269 !important;
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3, h4, h5, h6, p, label {
        color: #1D3269 !important;
    }
    textarea, .stTextArea textarea, .stTextInput input {
        background-color: #ffffff !important;
        color: #1D3269 !important;
        border: 1px solid #1D3269 !important;
        border-radius: 6px !important;
        padding: 8px !important;
        font-size: 15px !important;
    }
    

    .stButton > button,
    .stDownloadButton > button {
        background-color: #7FA536 !important;
        color: #ffffff !important;
        border: none;
        border-radius: 6px;
        font-size: 15px;
        padding: 8px 20px;
    }
    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background-color: #6d902f !important;
        transform: translateY(-1px);
    }

    audio {
        width: 100%;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("💬 Leitor de Texto com Voz Neural (Microsoft edge-tts)")

VOZES_PT = [
    "pt-BR-AntonioNeural",
    "pt-BR-FranciscaNeural",
    "pt-PT-DuarteNeural",
    "pt-PT-RaquelNeural"
]

with st.expander("📝 Nome do Projeto"):
    nome_projeto = st.text_input("Digite o nome do projeto:", value="meu_projeto").strip().replace(" ", "_")
    if not nome_projeto:
        st.warning("Por favor, digite um nome para o projeto.")
        st.stop()

with st.expander("⚙️ Configurações de Voz"):
    voz = st.selectbox("Escolha a voz", VOZES_PT)
    rate = st.slider("Velocidade (%)", -100, 100, 0)
    pitch = st.slider("Tom (semitons)", -20, 20, 0)



with st.expander("📦 Quantidade de Blocos"):
    num_blocos = st.selectbox("Selecione a quantidade de blocos:", list(range(1, 11)), index=1)

def ajustar_filtros(rate, pitch):
    return f"+{rate}%" if rate >= 0 else f"{rate}%", f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"

async def gerar_audio(texto, voice, rate, pitch, path_out):
    communicate = edge_tts.Communicate(text=texto, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(path_out)

def gerar_audio_sync(*args, **kwargs):
    asyncio.run(gerar_audio(*args, **kwargs))

def preview_audio(texto, voice, rate, pitch):
    with st.spinner("Gerando áudio..."):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        gerar_audio_sync(texto, voice, rate, pitch, temp.name)
        with open(temp.name, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<audio controls autoplay><source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)

def baixar_audio(texto, voice, rate, pitch, filename):
    os.makedirs("audios/mp3", exist_ok=True)
    os.makedirs("audios/wav", exist_ok=True)
    path = os.path.abspath(os.path.join("audios/mp3", filename))
    gerar_audio_sync(texto, voice, rate, pitch, path)
    with open(path, "rb") as f:
        st.download_button("⬇️ Baixar MP3", data=f, file_name=os.path.basename(path), mime="audio/mp3")

    wav_path = os.path.abspath(os.path.join("audios/wav", os.path.basename(path).replace(".mp3", ".wav")))
    os.system(f'ffmpeg -y -i "{path}" "{wav_path}"')
    with open(wav_path, "rb") as f_wav:
        st.download_button("⬇️ Baixar WAV", data=f_wav, file_name=os.path.basename(wav_path), mime="audio/wav")

def gerar_zip(blocos, voice, rate, pitch):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for i, texto in enumerate(blocos):
            if texto.strip():
                nome = f"{nome_projeto}_voz_{i+1}.mp3"
                os.makedirs("audios/mp3", exist_ok=True)
                os.makedirs("audios/wav", exist_ok=True)
                path = os.path.abspath(os.path.join("audios/mp3", nome))
                gerar_audio_sync(texto, voice, rate, pitch, path)
                with open(path, "rb") as f:
                    zip_file.writestr(f"{nome_projeto}/mp3/{nome}", f.read())

                wav_name = nome.replace(".mp3", ".wav")
                wav_path = os.path.abspath(os.path.join("audios/wav", os.path.basename(path).replace(".mp3", ".wav")))
                os.system(f'ffmpeg -y -i "{path}" "{wav_path}"')
                with open(wav_path, "rb") as fwav:
                    zip_file.writestr(f"{nome_projeto}/wav/{wav_name}", fwav.read())
    return zip_buffer.getvalue()

blocos = []
for i in range(num_blocos):
    texto = st.text_area(f"Texto para o Bloco {i+1}", key=f"texto_{i}")
    blocos.append(texto)
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"🔊 Preview {i+1}"):
            r, p = ajustar_filtros(rate, pitch)
            preview_audio(texto, voz, r, p)
    with col2:
        if st.button(f"💾 Baixar {i+1}"):
            r, p = ajustar_filtros(rate, pitch)
            filename = f"{nome_projeto}_voz_{i+1}.mp3"
            baixar_audio(texto, voz, r, p, filename)

if any(texto.strip() for texto in blocos):
    if st.button("📦 Baixar todos os áudios (.zip)"):
        with st.spinner("Gerando ZIP com todos os áudios..."):
            r, p = ajustar_filtros(rate, pitch)
            zip_data = gerar_zip(blocos, voz, r, p)
            st.download_button("📦 Download ZIP", data=zip_data, file_name=f"{nome_projeto}_audios_lote.zip", mime="application/zip")
