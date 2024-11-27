import streamlit as st
import openai
import pandas as pd
import os

# OpenAI APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# マニュアルデータを読み込み
def load_manual():
    if os.path.exists('manual.csv'):
        try:
            data = pd.read_csv('manual.csv', encoding='utf-8')
            if data.empty:
                st.error("manual.csv が空です。データを追加してください。")
                return pd.DataFrame(columns=['質問', '回答'])
            return data
        except pd.errors.EmptyDataError:
            st.error("manual.csv にデータがありません。")
            return pd.DataFrame(columns=['質問', '回答'])
        except Exception as e:
            st.error(f"manual.csv の読み込み中にエラーが発生しました: {e}")
            return pd.DataFrame(columns=['質問', '回答'])
    else:
        st.error("manual.csv が見つかりません。")
        return pd.DataFrame(columns=['質問', '回答'])

manual_data = load_manual()

def search_manual(question):
    for index, row in manual_data.iterrows():
        if row['質問'].lower() in question.lower():
            return row['回答']
    return None

def ask_bot(question, language):
    # OpenAIに質問を送信し、指定された言語で回答を取得
    system_message = f"You are a support bot that answers questions in {language}."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": question}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"An error occurred while contacting OpenAI: {e}"

# Streamlitアプリの設定
st.title("Q&A Bot")
st.write("This bot answers your questions. Please enter your question below.")

# 言語選択の追加
languages = ["English", "Filipino","Bahasa Indonesia", "Español", "Português", "日本語", "other"]
selected_language = st.selectbox("Please select your language:", languages)

question = st.text_input("Enter your question:")

if st.button("Submit"):
    if question:
        manual_response = search_manual(question)
        if manual_response:
            st.success(f"Manual Answer: {manual_response}")
        else:
            ai_response = ask_bot(question, selected_language)
            st.info(f"AI Answer: {ai_response} ※This question was not found in the manual.")
    else:
        st.warning("Please enter a question.")
