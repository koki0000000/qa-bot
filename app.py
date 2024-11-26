import streamlit as st
import openai
import pandas as pd

# OpenAI APIキーを環境変数から取得
import os
openai.api_key = os.getenv("OPENAI_API_KEY")

# マニュアルデータを読み込み
manual_data = pd.read_csv('manual.csv')

def search_manual(question):
    for index, row in manual_data.iterrows():
        if row['質問'].lower() in question.lower():
            return row['回答']
    return None

def ask_bot(question):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "あなたはマニュアルに基づいて回答するサポートボットです。"},
            {"role": "user", "content": question}
        ]
    )
    return response['choices'][0]['message']['content']

# Streamlitアプリの設定
st.title("Q&Aボット")
st.write("部下の質問に答えるためのボットです。質問を入力してください。")

question = st.text_input("質問を入力してください:")

if st.button("送信"):
    if question:
        manual_response = search_manual(question)
        if manual_response:
            st.success(f"マニュアル回答: {manual_response}")
        else:
            ai_response = ask_bot(question)
            st.info(f"AIからの回答: {ai_response}")
    else:
        st.warning("質問を入力してください。")
