import streamlit as st
import openai
import pandas as pd
import os
from difflib import get_close_matches

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

# 類似質問を検索する関数
def find_similar_question(question, manual_data, cutoff=0.6):
    questions = manual_data['質問'].tolist()
    matches = get_close_matches(question, questions, n=1, cutoff=cutoff)
    if matches:
        return matches[0]
    else:
        return None

def ask_bot(question, language):
    # OpenAIに質問を送信し、指定された言語で回答を取得
    system_message = f"You are a support bot that answers questions in {language} based on the provided manual."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": question}
            ]
        )
        return response['choices'][0]['message']['content']
    except openai.error.OpenAIError as e:
        return f"An error occurred while contacting OpenAI: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

# Streamlitアプリの設定
st.title("Q&A Bot")
st.write("This bot answers your questions based on the provided manual. Please enter your question below.")

# 言語選択の追加
languages = ["English", "Filipino", "Bahasa Indonesia", "Español", "Português", "日本語", "Other"]
selected_language = st.selectbox("Please select your language:", languages)

question = st.text_input("Enter your question:")

if st.button("Submit"):
    if question:
        # 正確な質問の検索
        manual_response = manual_data.loc[manual_data['質問'].str.lower() == question.lower(), '回答']
        if not manual_response.empty:
            st.success(f"Manual Answer: {manual_response.values[0]}")
        else:
            # 類似質問の検索
            similar_question = find_similar_question(question, manual_data)
            if similar_question:
                similar_answer = manual_data.loc[manual_data['質問'] == similar_question, '回答'].values[0]
                st.success(f"Similar Question Found: {similar_question}")
                st.success(f"Manual Answer: {similar_answer}")
            else:
                # 類似質問も見つからない場合、AIに回答を生成させる
                ai_response = ask_bot(question, selected_language)
                st.info(f"AI Answer: {ai_response} ※This question was not found in the manual. Ask koki.")
    else:
        st.warning("Please enter a question.")
