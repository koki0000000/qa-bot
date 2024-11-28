import streamlit as st
import openai
import pandas as pd
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# -------------------------------
# OpenAI API Key Setup
# -------------------------------
# OpenAI APIキーを環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------
# Google Drive Authentication
# -------------------------------
def authenticate_google_drive():
    """
    Google Driveに認証し、Driveオブジェクトを返す関数
    """
    gauth = GoogleAuth()
    # credentials.json ファイルのパスを指定
    gauth.LoadServiceConfigFile('credentials.json')
    gauth.ServiceAuth()
    drive = GoogleDrive(gauth)
    return drive

# Google Driveに認証
drive = authenticate_google_drive()

# アップロード先のGoogle DriveフォルダID
folder_id = '1ifXllfufA5EVGlWVEk8RAYvrQKE-5Ox9'  # ご提供のフォルダIDに置き換えてください

# -------------------------------
# File Upload Function
# -------------------------------
def upload_file_to_drive(drive, file_path, folder_id):
    """
    指定されたファイルをGoogle Driveの指定フォルダにアップロードまたは更新する関数
    """
    file_name = os.path.basename(file_path)
    # 同じ名前のファイルがフォルダ内に存在するか確認
    file_list = drive.ListFile({
        'q': f"title='{file_name}' and '{folder_id}' in parents and trashed=false"
    }).GetList()
    if file_list:
        # 既存のファイルを更新
        file = file_list[0]
        file.SetContentFile(file_path)
        file.Upload()
        print(f'Updated {file_name} in Google Drive.')
    else:
        # 新しいファイルをアップロード
        gfile = drive.CreateFile({'parents': [{'id': folder_id}], 'title': file_name})
        gfile.SetContentFile(file_path)
        gfile.Upload()
        print(f'Uploaded {file_name} to Google Drive.')

# -------------------------------
# Streamlit App Configuration
# -------------------------------

# カスタムCSSを適用してスタイルを設定
st.markdown(
    """
    <style>
    /* 全体の背景色 */
    .stApp {
        background-color: #000000;
        font-family: 'Helvetica Neue', sans-serif;
    }
    /* タイトルのスタイル */
    h1 {
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 20px;
    }
    /* サイドバーのスタイル */
    .css-1d391kg {
        background-color: #1a1a1a;
    }
    .css-1d391kg .css-hxt7ib {
        color: #FFFFFF;
    }
    /* 入力フィールドのスタイル */
    .stTextInput, .stTextArea {
        margin-bottom: 20px;
    }
    .stTextInput>div>div>input, .stTextArea textarea {
        background-color: #333333;
        color: #FFFFFF;
    }
    /* ボタンのスタイル */
    .stButton>button {
        background-color: #0066cc;
        color: #FFFFFF;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
        margin-top: 10px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #0052a3;
    }
    /* 質問と回答のスタイル */
    .question, .answer {
        background-color: #1a1a1a;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        color: #FFFFFF;
    }
    .question {
        border-left: 5px solid #0066cc;
    }
    .answer {
        border-left: 5px solid #00cc66;
    }
    /* フィードバックセクションのスタイル */
    .feedback-section {
        margin-top: -10px;
        margin-bottom: 20px;
    }
    .stRadio>div {
        flex-direction: row;
        color: #FFFFFF;
    }
    .stRadio>div>label {
        margin-right: 10px;
    }
    /* データフレームのスタイル */
    .stDataFrame {
        margin-top: 20px;
        color: #FFFFFF;
    }
    /* テキストカラーを全体的に調整 */
    .css-1e5imcs, .css-1v3fvcr {
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# Load Manual Data
# -------------------------------
def load_manual_data():
    """
    manual.csv ファイルをロードし、データフレームを返す関数
    """
    if os.path.exists('manual.csv'):
        try:
            data = pd.read_csv('manual.csv', encoding='utf-8')
            if data.empty:
                st.error("The manual.csv file is empty. Please add data.")
                return pd.DataFrame(columns=['質問', '回答'])
            return data
        except pd.errors.EmptyDataError:
            st.error("The manual.csv file has no data.")
            return pd.DataFrame(columns=['質問', '回答'])
        except Exception as e:
            st.error(f"An error occurred while loading manual.csv: {e}")
            return pd.DataFrame(columns=['質問', '回答'])
    else:
        st.error("The manual.csv file was not found.")
        return pd.DataFrame(columns=['質問', '回答'])

manual_data = load_manual_data()

# manual_data をセッションステートに保存
if 'manual_data' not in st.session_state:
    st.session_state['manual_data'] = manual_data
else:
    manual_data = st.session_state['manual_data']

# 質問履歴のセッションステートを初期化
if 'history' not in st.session_state:
    st.session_state['history'] = []

# -------------------------------
# Page Selection
# -------------------------------
page = st.sidebar.selectbox(
    "Select a page",
    ["User", "Admin"],
    index=0,
    key='page_selection'
)

# -------------------------------
# User Page
# -------------------------------
if page == "User":
    # アプリの設定
    st.title("💬 Q&A Bot")
    st.write("This bot answers your questions based on the manual. Please enter your question below.")
    
    # ベータ版の注釈を追加
    st.markdown(
        """
        <div style='background-color: #333333; padding: 10px; border-radius: 5px; margin-bottom: 20px;'>
            <span style='color: #FFFFFF; font-size: 16px;'>
                <strong>This is a beta version. Your active feedback would be greatly appreciated!</strong>
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    question = st.text_input("Enter your question:")
    
    if st.button("Submit"):
        if question:
            # マニュアルの内容をテキストに結合
            manual_text = "\n".join(manual_data['質問'] + "\n" + manual_data['回答'])
    
            # 質問とマニュアルをOpenAIに送り、回答を取得
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an assistant who answers the user's questions based solely on the provided manual."
                                " Please answer in the same language as the user's question."
                                " Do not provide information not included in the manual, but use the knowledge from the manual to answer flexibly."
                            )
                        },
                        {"role": "user", "content": f"Manual:\n{manual_text}\n\nUser's question:\n{question}"}
                    ]
                )
                ai_response = response['choices'][0]['message']['content']
                st.success("The answer has been generated. Please see below.")
    
                # 質問と回答を表示
                st.markdown(f"<div class='question'><strong>Question:</strong> {question}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='answer'><strong>Answer:</strong> {ai_response}</div>", unsafe_allow_html=True)
    
                # 質問と回答を履歴に追加
                st.session_state['history'].append({'question': question, 'answer': ai_response, 'feedback': "Not Rated"})
    
                # 質問と回答を 'questions.csv' に保存
                def save_question():
                    if os.path.exists('questions.csv'):
                        try:
                            question_data = pd.read_csv('questions.csv', encoding='utf-8')
                        except pd.errors.EmptyDataError:
                            question_data = pd.DataFrame(columns=['question', 'answer', 'feedback'])
                    else:
                        question_data = pd.DataFrame(columns=['question', 'answer', 'feedback'])
    
                    new_row = {
                        'question': question,
                        'answer': ai_response,
                        'feedback': "Not Rated"
                    }
                    question_data = pd.concat([question_data, pd.DataFrame([new_row])], ignore_index=True)
                    question_data.to_csv('questions.csv', index=False, encoding='utf-8')
                    # Google Drive にアップロード
                    upload_file_to_drive(drive, 'questions.csv', folder_id)
    
                save_question()
    
            except openai.error.OpenAIError as e:
                st.error(f"An error occurred while contacting OpenAI: {e}")
        else:
            st.warning("Please enter a question.")
    
    # 新しい順に質問履歴を表示
    st.markdown("## 🕘 Question History")
    for idx, qa in enumerate(reversed(st.session_state['history'])):
        actual_idx = len(st.session_state['history']) - idx - 1
        st.markdown(f"<div class='question'><strong>Question {actual_idx+1}:</strong> {qa['question']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='answer'><strong>Answer {actual_idx+1}:</strong> {qa['answer']}</div>", unsafe_allow_html=True)
    
        if qa['feedback'] == "Not Rated":
            # フィードバックセクションを回答の直下に配置
            st.markdown("<div class='feedback-section'>", unsafe_allow_html=True)
            feedback = st.radio(
                "Was this answer helpful?",
                ["Yes", "No"],
                key=f"feedback_{actual_idx}",
                index=0
            )
            if st.button("Submit Feedback", key=f"submit_feedback_{actual_idx}"):
                qa['feedback'] = feedback
                st.success("Thank you for your feedback!")
    
                # 'questions.csv' のフィードバックを更新
                if os.path.exists('questions.csv'):
                    question_data = pd.read_csv('questions.csv', encoding='utf-8')
                    mask = (question_data['question'] == qa['question']) & (question_data['answer'] == qa['answer'])
                    question_data.loc[mask, 'feedback'] = feedback
                    question_data.to_csv('questions.csv', index=False, encoding='utf-8')
                    # Google Drive にアップロード
                    upload_file_to_drive(drive, 'questions.csv', folder_id)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"**Feedback {actual_idx+1}:** {qa['feedback']}")

# -------------------------------
# Admin Page
# -------------------------------
elif page == "Admin":
    # 管理者認証
    admin_password = st.sidebar.text_input("Enter the password", type="password")
    if admin_password == "koki":  # 任意のパスワードに変更してください
        st.success("Accessed the admin page.")
    
        # 入力をクリアする関数
        def clear_inputs():
            st.session_state["new_question_value"] = ""
            st.session_state["new_answer_value"] = ""
    
        # 新しいQ&Aを追加
        st.markdown("## ➕ Add New Q&A")
        new_question = st.text_input("Enter a new question", key="new_question", value=st.session_state.get("new_question_value", ""))
        new_answer = st.text_area("Enter a new answer", key="new_answer", value=st.session_state.get("new_answer_value", ""))
        if st.button("Add"):
            if new_question and new_answer:
                new_row = pd.DataFrame({'質問': [new_question], '回答': [new_answer]})
                st.session_state['manual_data'] = pd.concat([st.session_state['manual_data'], new_row], ignore_index=True)
                st.session_state['manual_data'].to_csv('manual.csv', index=False, encoding='utf-8')
                st.success("The new Q&A has been added.")
    
                # 入力フィールドをクリア
                clear_inputs()
    
                # 更新されたマニュアルをGoogle Driveにアップロード
                upload_file_to_drive(drive, 'manual.csv', folder_id)
    
            else:
                st.warning("Please enter both a question and an answer.")
    
        # 更新されたマニュアルデータを表示
        st.markdown("## 📄 Current Manual")
        st.dataframe(st.session_state['manual_data'])
    
        # すべての質問とフィードバックを表示
        st.markdown("## 📊 All Questions and Feedback")
        if os.path.exists('questions.csv'):
            try:
                question_data = pd.read_csv('questions.csv', encoding='utf-8')
                if not question_data.empty:
                    st.dataframe(question_data)
                    positive_feedback = question_data[question_data['feedback'] == 'Yes'].shape[0]
                    negative_feedback = question_data[question_data['feedback'] == 'No'].shape[0]
                    st.markdown(f"**Helpful:** {positive_feedback}")
                    st.markdown(f"**Not Helpful:** {negative_feedback}")
                else:
                    st.warning("There are no questions yet.")
            except pd.errors.EmptyDataError:
                st.warning("There are no questions yet.")
        else:
            st.warning("There are no questions yet.")
    
        # オプションで questions.csv ファイルをダウンロード
        if os.path.exists('questions.csv'):
            with open('questions.csv', 'rb') as f:
                st.download_button('Download Questions Data', f, file_name='questions.csv')
    else:
        st.error("Incorrect password.")
