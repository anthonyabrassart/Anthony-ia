import io
import os
import subprocess
import uuid
from google import genai
from google.genai import types
import pandas as pd
import streamlit as st
# ------------------------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & NOM DE L'IA
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Anthony IA",
    page_icon="🤖",
    layout="wide"
)

# Empêcher la traduction automatique de Google Traduction
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)


api_key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"  # Modèle rapide et multimodal

# ------------------------------------------------------------------------------
# 2. GESTION DE L'HISTORIQUE DE DISCUSSION
# ------------------------------------------------------------------------------
if "chats" not in st.session_state:
    st.session_state.chats = {}

if "current_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.chats[new_id] = {
        "title": "Nouvelle discussion",
        "messages": [],
    }
    st.session_state.current_chat_id = new_id


def create_new_chat():
    new_id = str(uuid.uuid4())
    st.session_state.chats[new_id] = {
        "title": f"Chat {len(st.session_state.chats) + 1}",
        "messages": [],
    }
    st.session_state.current_chat_id = new_id


# Barre latérale (Sidebar) pour l'historique
with st.sidebar:
    st.title("🤖 Anthony IA")
    if st.button("➕ Nouvelle discussion", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.markdown("---")
    st.subheader("📚 Historique des discussions")

    chat_ids = list(st.session_state.chats.keys())
    for cid in chat_ids:
        chat_data = st.session_state.chats[cid]
        col1, col2 = st.columns([4, 1])
        with col1:
            is_active = cid == st.session_state.current_chat_id
            btn_label = (
                f"👉 {chat_data['title']}"
                if is_active
                else f"💬 {chat_data['title']}"
            )
            if st.button(
                btn_label, key=f"select_{cid}", use_container_width=True
            ):
                st.session_state.current_chat_id = cid
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{cid}"):
                del st.session_state.chats[cid]
                if st.session_state.current_chat_id == cid:
                    remaining = list(st.session_state.chats.keys())
                    if remaining:
                        st.session_state.current_chat_id = remaining[0]
                    else:
                        create_new_chat()
                st.rerun()

# ------------------------------------------------------------------------------
# STRUCTURE PAR ONGLETS
# ------------------------------------------------------------------------------
tab_chat, tab_aider = st.tabs(
    ["💬 Chat Anthony IA", "💻 Agent Aider & Terminal CMD"]
)

current_chat = st.session_state.chats[st.session_state.current_chat_id]

# ==============================================================================
# ONGLET 1 : CHAT ANTHONY IA (AVEC FICHIERS & MULTIMODALITÉ)
# ==============================================================================
with tab_chat:
    st.title("Anthony IA")
    st.caption("Votre assistant IA multimodal avec gestion de fichiers et mémoire")

    # Affichage des anciens messages
    for msg in current_chat["messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "files_summary" in msg:
                st.info(f"📁 Fichiers joints : {msg['files_summary']}")

    # 3. INSERTION DE FICHIERS (PDF, Excel, Images, TXT, CSV)
    uploaded_files = st.file_uploader(
        "📎 Joindre des fichiers à la question (PDF, Excel, PNG/JPEG, CSV, TXT...)",
        accept_multiple_files=True,
        type=["pdf", "xlsx", "xls", "csv", "png", "jpg", "jpeg", "txt"],
    )

    # Zone de saisie du message
    if prompt := st.chat_input("Posez votre question à Anthony IA..."):
        # Mise à jour automatique du titre de la discussion
        if len(current_chat["messages"]) == 0:
            current_chat["title"] = prompt[:25] + (
                "..." if len(prompt) > 25 else ""
            )

        contents = []
        files_info = []

        # Traitement des fichiers importés
        if uploaded_files:
            for f in uploaded_files:
                files_info.append(f.name)
                bytes_data = f.read()

                if f.name.lower().endswith((".png", ".jpg", ".jpeg")):
                    contents.append(
                        types.Part.from_bytes(
                            data=bytes_data, mime_type=f.type
                        )
                    )
                elif f.name.lower().endswith(".pdf"):
                    contents.append(
                        types.Part.from_bytes(
                            data=bytes_data, mime_type="application/pdf"
                        )
                    )
                elif f.name.lower().endswith((".xlsx", ".xls")):
                    try:
                        df = pd.read_excel(io.BytesIO(bytes_data))
                        contents.append(
                            f"\n[Contenu de l'Excel {f.name}]:\n{df.to_string(max_rows=50)}\n"
                        )
                    except Exception as e:
                        contents.append(f"\n[Erreur lecture Excel {f.name}: {e}]\n")
                elif f.name.lower().endswith(".csv"):
                    try:
                        df = pd.read_csv(io.BytesIO(bytes_data))
                        contents.append(
                            f"\n[Contenu du CSV {f.name}]:\n{df.to_string(max_rows=50)}\n"
                        )
                    except Exception as e:
                        contents.append(f"\n[Erreur lecture CSV {f.name}: {e}]\n")
                elif f.name.lower().endswith(".txt"):
                    text_str = bytes_data.decode("utf-8", errors="ignore")
                    contents.append(
                        f"\n[Contenu du fichier texte {f.name}]:\n{text_str}\n"
                    )

        contents.append(prompt)

        # Sauvegarde du message utilisateur
        user_msg = {"role": "user", "content": prompt}
        if files_info:
            user_msg["files_summary"] = ", ".join(files_info)
        current_chat["messages"].append(user_msg)

        # Affichage à l'écran
        with st.chat_message("user"):
            st.write(prompt)
            if files_info:
                st.info(f"📁 Fichiers joints : {', '.join(files_info)}")

        # Appel de l'IA Anthony IA
        with st.chat_message("assistant"):
            with st.spinner("Anthony IA analyse votre demande..."):
                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME, contents=contents
                    )
                    st.write(response.text)
                    current_chat["messages"].append(
                        {"role": "assistant", "content": response.text}
                    )
                except Exception as e:
                    err = f"❌ Erreur : {e}"
                    st.error(err)
                    current_chat["messages"].append(
                        {"role": "assistant", "content": err}
                    )

# ==============================================================================
# ONGLET 2 : AGENT AIDER & TERMINAL CMD
# ==============================================================================
with tab_aider:
    st.title("💻 Agent Aider & Terminal CMD")
    st.caption("Pilotez Aider pour modifier votre code ou lancez des commandes système.")

    mode = st.radio(
        "Sélectionnez le mode d'action :",
        ["🤖 Consigne Aider (Codage)", "⚡ Commande Terminal (CMD)"],
        horizontal=True,
    )

   if mode == "🤖 Consigne Aider (Codage)":
    instruction = st.text_area(
        "Consigne pour l'agent Aider :",
        placeholder="Ex : Ajout d'un bouton d'export du chat en texte...",
    )
    file_target = st.text_input("Fichier cible :", value="app.py")

    if st.button("🚀 Exécuter Aider"):
        if instruction:
            cmd = f'python3 -m aider --message "{instruction}" --yes-always {file_target}'
            st.info(f"Commande exécutée : `{cmd}`")
            with st.spinner("Aider modifie le code..."):
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            st.subheader("Retour d'Aider :")
            st.code(result.stdout if result.stdout else result.stderr)
        else:
            st.warning("Veuillez saisir une consigne.")

    else:
        cmd_text = st.text_input(
            "Commande système à lancer :", placeholder="dir ou py -3.12 --version"
        )
        if st.button("▶️ Lancer la commande"):
            if cmd_text:
                with st.spinner("Exécution..."):
                    res = subprocess.run(
                        cmd_text, shell=True, capture_output=True, text=True
                    )
                    st.subheader("Résultat (STDOUT) :")
                    st.code(res.stdout if res.stdout else "Aucune sortie.")
                    if res.stderr:
                        st.subheader("Erreurs (STDERR) :")
                        st.code(res.stderr)
            else:
                st.warning("Veuillez entrer une commande.")
