import streamlit as st
from langchain.chains import RetrievalQA
from langchain_openai import OpenAI
from langchain_community.document_loaders import CSVLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
import os

st.set_page_config(page_title="Fußball-Chatbot", page_icon="⚽️")
st.write("# Willkommen beim Fußball-Chatbot! ⚽️")

openai_api_key = "XXXX"

try:
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
except Exception as e:
    st.error(f"Fehler beim Erstellen der Embeddings: {str(e)}")
    openai_api_key = st.text_input("Bitte geben Sie Ihren eigenen OpenAI API-Schlüssel ein:", type="password")
    st.write("Hinweis: Sie können einen API-Schlüssel unter https://platform.openai.com/api-keys erstellen.")

    if openai_api_key:
        try:
            embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
            st.success("Eigener API-Schlüssel erfolgreich verwendet.")
        except Exception as e:
            st.error(f"Fehler beim Erstellen der Embeddings mit eigenem API-Schlüssel: {str(e)}")
            st.stop()

# Persistente Vektordatenbank mit Indizierung
persist_directory = 'db'

# Streamlit-App mit Tabs
tab1, tab2 = st.tabs(["Vektordatenbank", "Chatbot"])

with tab1:
    st.header("Vektordatenbank")
    
    if not os.path.exists(persist_directory):
        st.write(f"Vektordatenbank nicht gefunden. Klicke auf den Button, um eine neue Datenbank im Verzeichnis {persist_directory} zu erstellen.")
        if st.button("Vektordatenbank erstellen"):
            # Laden der CSV-Datei mit Fußballspielerdaten
            csv_file = "fussballspieler_daten.csv"
            st.write(f"Lade Daten aus der CSV-Datei: {csv_file}")
            loader = CSVLoader(file_path=csv_file, encoding="utf-8")
            data = loader.load()
            st.write(f"Daten erfolgreich geladen. Anzahl der geladenen Dokumente: {len(data)}")

            # Textaufteilung und Erstellung des Vektorspeichers
            st.write("Teile Texte auf...")
            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
            texts = text_splitter.split_documents(data)
            st.write(f"Texte erfolgreich aufgeteilt. Anzahl der Text-Chunks: {len(texts)}")

            st.write(f"Erstelle persistente Vektordatenbank im Verzeichnis: {persist_directory}")
            vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

            # Texte in Batches hinzufügen, um Ratenbegrenzung zu vermeiden
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                vectorstore.add_documents(batch_texts)

            st.write(f"Vektordatenbank erfolgreich erstellt und gespeichert.")
            
            # Erstellung des RetrievalQA-Objekts
            st.write("Erstelle das RetrievalQA-Objekt...")
            qa = RetrievalQA.from_chain_type(
                llm=OpenAI(openai_api_key=openai_api_key),
                chain_type="stuff",
                retriever=vectorstore.as_retriever(search_kwargs={"k": 1}),
            )
            st.session_state.qa = qa
            st.session_state.vectorstore = vectorstore
            st.write("RetrievalQA-Objekt erfolgreich erstellt.")
    else:
        st.write(f"Lade existierende Vektordatenbank aus dem Verzeichnis: {persist_directory}")
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
        st.write(f"Vektordatenbank erfolgreich geladen.")

        # Definition der Rolle des Chatbots
        template = (
            "Du bist ein hilfsbereiter Fußball-Experte, der detaillierte Informationen zu Fußballspielern liefert "
            "und bei Fragen, die nicht direkt beantwortet werden können, alternative Vorschläge macht."
        )
        system_message_prompt = SystemMessagePromptTemplate.from_template(template)
        human_template = "{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

        # Erstellung des ConversationalRetrievalChain-Objekts mit angepassten Parametern
        st.write("Erstelle das ConversationalRetrievalChain-Objekt...")
        qa = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(openai_api_key=openai_api_key, model_name="gpt-4", temperature=1, max_tokens=512),
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        )
        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
        st.session_state.qa = qa
        st.session_state.chat_history = []
        st.write("ConversationalRetrievalChain-Objekt erfolgreich erstellt.")

with tab2:
    if 'qa' not in st.session_state:
        st.warning("Bitte laden Sie zuerst die Vektordatenbank im Tab 'Vektordatenbank'.")
    else:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        user_input = st.text_input("Stellen Sie eine Frage zu einem Fußballspieler:", key="input")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})

            qa = st.session_state.qa
            chat_history = [
                (message["content"], message["content"])
                for message in st.session_state.messages
                if message["role"] in ["user", "assistant"]
            ]

            result = qa({"question": user_input, "chat_history": chat_history})
            response = result['answer']

            st.session_state.messages.append({"role": "assistant", "content": response})

        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                if message["role"] == "user":
                    st.chat_message("user", avatar="🧑‍💻").write(message["content"])
                else:
                    st.chat_message("assistant", avatar="⚽️").write(message["content"])