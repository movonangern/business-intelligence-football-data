import streamlit as st
from langchain.chains import RetrievalQA
from langchain_openai import OpenAI
from langchain_community.document_loaders import CSVLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
import os

st.set_page_config(page_title="Fußball-Chatbot", page_icon="⚽️")
st.write("# Willkommen beim Fußball-Chatbot! ⚽️")

# Hier wird der openai_api_key als Parameter übergeben
openai_api_key = "XXX"
embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

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

        # Erstellung des ConversationalRetrievalChain-Objekts mit angepassten Parametern
        st.write("Erstelle das ConversationalRetrievalChain-Objekt...")
        qa = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(openai_api_key=openai_api_key, model_name="gpt-3.5-turbo", temperature=1, max_tokens=512),
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        )
        st.session_state.qa = qa
        st.session_state.chat_history = []
        st.write("ConversationalRetrievalChain-Objekt erfolgreich erstellt.")

with tab2:
    st.header("Fußball-Chatbot")

    if 'qa' not in st.session_state:
        st.warning("Bitte laden Sie zuerst die Vektordatenbank im Tab 'Vektordatenbank'.")
    else:
        user_input = st.text_input("Stellen Sie eine Frage zu einem Fußballspieler:")
        if user_input:
            st.write(f"Frage: {user_input}")

            # Fortschrittsanzeige für die Antwortgenerierung
            progress_text = "Antwort wird generiert. Bitte warten..."
            my_bar = st.progress(0, text=progress_text)

            qa = st.session_state.qa
            chat_history = st.session_state.chat_history
            
            # Antwort generieren
            result = qa({"question": user_input, "chat_history": chat_history})
            response = result['answer']
            
            # Chat-Verlauf aktualisieren
            chat_history.append((user_input, response))
            st.session_state.chat_history = chat_history

            # Fortschrittsanzeige auf 100% setzen
            my_bar.progress(1.0, text="Antwort erfolgreich generiert.")

            st.write(f"Antwort: {response}")