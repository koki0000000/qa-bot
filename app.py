import streamlit as st
import openai
import pandas as pd
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# -------------------------------
# OpenAI API Key Setup
# -------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------
# Google Drive Authentication
# -------------------------------
def authenticate_google_drive():
    """
    Google Driveにサービスアカウントを使用して認証し、Driveサービスオブジェクトを返す関数
    """
    credentials_json = os.getenv("GDRIVE_CREDENTIALS")
    if not credentials_json:
        raise ValueError("GDRIVE_CREDENTIALS 環境変数が設定されていません。")
    
    try:
        service_account_info = json.loads(credentials_json)
    except json.JSONDecodeError:
        raise ValueError("GDRIVE_CREDENTIALS 環境変数のJSONが無効です。")
    
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    
    service = build('drive', 'v3', credentials=credentials)
    return service

# Google Driveに認証
try:
    drive_service = authenticate_google_drive()
except Exception as e:
    st.error(f"Google Drive authentication failed: {e}")

# アップロード先のGoogle DriveフォルダID
folder_id = '1ifXllfufA5EVGlWVEk8RAYvrQKE-5Ox9'  # ご提供のフォルダIDに置き換えてください

# -------------------------------
# File Upload Function
# -------------------------------
def upload_file_to_drive(service, file_path, folder_id):
    """
    指定されたファイルをGoogle Driveの指定フォルダにアップロードまたは更新する関数
    """
    file_name = os.path.basename(file_path)
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    try:
        # ファイルが既に存在するか確認
        existing_files = service.files().list(
            q=f"name='{file_name}' and '{folder_id}' in parents and trashed=false",
            fields='files(id, name)'
        ).execute()
        if existing_files['files']:
            # 既存のファイルを更新
            file_id = existing_files['files'][0]['id']
            service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            st.write(f'Updated {file_name} in Google Drive.')
        else:
            # 新しいファイルをアップロード
            service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            st.write(f'Uploaded {file_name} to Google Drive.')
    except Exception as e:
        st.error(f"Failed to upload {file_name} to Google Drive: {e}")

# -------------------------------
# Streamlit App Configuration
# -------------------------------
# カスタムCSSを適用してスタイルを設定（必要に応じて）
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
    /* 質問ボタンのスタイル */
    .question-button {
        display: inline-block;
        width: 100px;
        height: 100px;
        margin: 10px;
        border-radius: 50%;
        background-color: #333333;
        color: #FFFFFF;
        text-align: center;
        line-height: 100px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .question-button:hover {
        background-color: #555555;
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
            # 'priority' 列の欠損値を許容し、Int64型に変換（欠損値を許容）
            if 'priority' in data.columns:
                data['priority'] = pd.to_numeric(data['priority'], errors='coerce').astype('Int64')
            else:
                # 'priority' 列がない場合は追加（全てNaN）
                data['priority'] = pd.Series([pd.NA] * len(data))
            if data.empty:
                st.error("The manual.csv file is empty. Please add data.")
                return pd.DataFrame(columns=['question', 'answer', 'priority'])
            return data
        except pd.errors.EmptyDataError:
            st.error("The manual.csv file has no data.")
            return pd.DataFrame(columns=['question', 'answer', 'priority'])
        except Exception as e:
            st.error(f"An error occurred while loading manual.csv: {e}")
            return pd.DataFrame(columns=['question', 'answer', 'priority'])
    else:
        st.error("The manual.csv file was not found.")
        return pd.DataFrame(columns=['question', 'answer', 'priority'])

manual_data = load_manual_data()

# manual_data をセッションステートに保存
if 'manual_data' not in st.session_state:
    st.session_state['manual_data'] = manual_data
else:
    manual_data = st.session_state['manual_data']

# -------------------------------
# Load Feedback Data
# -------------------------------
def load_feedback_data():
    """
    feedback.csv ファイルをロードし、データフレームを返す関数
    """
    if os.path.exists('feedback.csv'):
        try:
            data = pd.read_csv('feedback.csv', encoding='utf-8')
            if data.empty:
                st.warning("The feedback.csv file is empty.")
                return pd.DataFrame(columns=['question', 'answer', 'feedback'])
            return data
        except pd.errors.EmptyDataError:
            st.warning("The feedback.csv file has no data.")
            return pd.DataFrame(columns=['question', 'answer', 'feedback'])
        except Exception as e:
            st.error(f"An error occurred while loading feedback.csv: {e}")
            return pd.DataFrame(columns=['question', 'answer', 'feedback'])
    else:
        return pd.DataFrame(columns=['question', 'answer', 'feedback'])

feedback_data = load_feedback_data()

# feedback_data をセッションステートに保存
if 'feedback_data' not in st.session_state:
    st.session_state['feedback_data'] = feedback_data
else:
    feedback_data = st.session_state['feedback_data']

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

    # よくある質問のセクション
    st.markdown("## 📝 Frequently Asked Questions")
    faq_questions = manual_data[manual_data['priority'] == 1]['question'].dropna().tolist()

    if faq_questions:
        # 質問ボタンを表示
        num_columns = 3  # 列数を調整
        cols = st.columns(num_columns)
        for idx, question in enumerate(faq_questions):
            with cols[idx % num_columns]:
                if st.button(question, key=f"faq_{idx}"):
                    st.session_state['selected_question'] = question
    else:
        st.info("No high priority (priority=1) questions found.")

    # 質問入力欄
    if 'selected_question' in st.session_state:
        question = st.text_input("Enter your question:", value=st.session_state['selected_question'], key="selected_question_input")
    else:
        question = st.text_input("Enter your question:")

    if st.button("Submit"):
        if question:
            # マニュアルの内容をテキストに結合
            manual_text = "\n".join(manual_data['question'].fillna('') + "\n" + manual_data['answer'].fillna(''))

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
                new_feedback = pd.DataFrame([{
                    'question': question,
                    'answer': ai_response,
                    'feedback': pd.NA  # 初期値は未評価
                }])
                st.session_state['feedback_data'] = pd.concat([st.session_state['feedback_data'], new_feedback], ignore_index=True)

                # 質問と回答を 'feedback.csv' に保存
                def save_feedback():
                    st.session_state['feedback_data'].to_csv('feedback.csv', index=False, encoding='utf-8')
                    # Google Drive にアップロード
                    upload_file_to_drive(drive_service, 'feedback.csv', folder_id)

                save_feedback()

            except openai.error.OpenAIError as e:
                st.error(f"An error occurred while contacting OpenAI: {e}")
        else:
            st.warning("Please enter a question.")

    # 質問履歴の表示
    st.markdown("## 🕘 Question History")
    if not st.session_state['feedback_data'].empty:
        for idx, qa in enumerate(reversed(st.session_state['feedback_data'].to_dict('records'))):
            actual_idx = len(st.session_state['feedback_data']) - idx - 1
            st.markdown(f"<div class='question'><strong>Question {actual_idx+1}:</strong> {qa['question']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='answer'><strong>Answer {actual_idx+1}:</strong> {qa['answer']}</div>", unsafe_allow_html=True)

            if pd.isna(qa['feedback']):
                # フィードバックセクションを回答の直下に配置
                st.markdown("<div class='feedback-section'>", unsafe_allow_html=True)
                feedback = st.radio(
                    "Was this answer helpful?",
                    ["Yes", "No"],
                    key=f"feedback_{actual_idx}",
                    index=0
                )
                if st.button("Submit Feedback", key=f"submit_feedback_{actual_idx}"):
                    st.session_state['feedback_data'].at[actual_idx, 'feedback'] = feedback
                    st.success("Thank you for your feedback!")

                    # 'feedback.csv' のフィードバックを更新
                    def update_feedback():
                        st.session_state['feedback_data'].to_csv('feedback.csv', index=False, encoding='utf-8')
                        # Google Drive にアップロード
                        upload_file_to_drive(drive_service, 'feedback.csv', folder_id)

                    update_feedback()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"**Feedback {actual_idx+1}:** {qa['feedback']}")
    else:
        st.info("No questions have been asked yet.")

# -------------------------------
# Admin Page
# -------------------------------
elif page == "Admin":
    # 管理者認証
    admin_password = st.sidebar.text_input("Enter the password", type="password")
    # 環境変数から管理者パスワードを取得
    stored_admin_password = os.getenv("ADMIN_PASSWORD")
    if not stored_admin_password:
        st.error("ADMIN_PASSWORD 環境変数が設定されていません。")
    elif admin_password == stored_admin_password:
        st.success("Accessed the admin page.")

        # ---------------------------
        # Manage Manual.csv
        # ---------------------------
        st.markdown("## ➕ Manage Manual")

        # 新しいQ&Aを追加するフォーム
        with st.expander("Add New Q&A"):
            new_question = st.text_input("Enter a new question")
            new_answer = st.text_area("Enter a new answer")
            set_priority = st.checkbox("Set priority")
            if set_priority:
                new_priority = st.number_input("Enter priority (1 for high priority)", min_value=1, step=1, value=2, key="new_priority")
            else:
                new_priority = pd.NA  # 未設定の場合はNaN

            if st.button("Add Q&A"):
                if new_question and new_answer:
                    new_row = pd.DataFrame({
                        'question': [new_question],
                        'answer': [new_answer],
                        'priority': [new_priority]
                    })
                    st.session_state['manual_data'] = pd.concat([st.session_state['manual_data'], new_row], ignore_index=True)
                    st.session_state['manual_data'].to_csv('manual.csv', index=False, encoding='utf-8')
                    st.success("New Q&A has been added.")
                    # Google Drive にアップロード
                    upload_file_to_drive(drive_service, 'manual.csv', folder_id)
                else:
                    st.warning("Please enter both a question and an answer.")

        # ---------------------------
        # Current Manual Data (DataFrame View) with Edit Buttons
        # ---------------------------
        st.markdown("### 📄 Current Manual Data (DataFrame View)")

        manual_data = st.session_state['manual_data']

        if not manual_data.empty:
            for idx, row in manual_data.iterrows():
                # 各行に「Edit」ボタンを追加
                cols = st.columns([8, 2])  # データとボタンの割合を調整
                with cols[0]:
                    st.markdown(f"**Question {idx + 1}:** {row['question']}")
                    # スニペット表示
                    if len(row['question']) > 100:
                        display_question = row['question'][:100] + "..."
                    else:
                        display_question = row['question']
                    if len(row['answer']) > 100:
                        display_answer = row['answer'][:100] + "..."
                    else:
                        display_answer = row['answer']
                    st.markdown(f"**Answer:** {display_answer}")
                    priority_display = row['priority'] if not pd.isna(row['priority']) else "Not Set"
                    st.markdown(f"**Priority:** {priority_display}")
                with cols[1]:
                    edit_button = st.button("Edit", key=f"edit_button_{idx}")

                if edit_button:
                    # 編集フォームを表示
                    with st.expander(f"Editing Q&A {idx + 1}", expanded=True):
                        # フルテキスト表示と編集フィールド
                        edited_question = st.text_area("Question", value=row['question'], height=100, key=f"edit_question_{idx}")
                        edited_answer = st.text_area("Answer", value=row['answer'], height=150, key=f"edit_answer_{idx}")
                        set_edit_priority = st.checkbox("Set priority", key=f"set_edit_priority_checkbox_{idx}")
                        if set_edit_priority:
                            edited_priority = st.number_input(
                                "Priority", 
                                min_value=1, 
                                step=1, 
                                value=int(row['priority']) if not pd.isna(row['priority']) else 2, 
                                key=f"edit_priority_{idx}"
                            )
                        else:
                            edited_priority = pd.NA  # 未設定の場合はNaN

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Save Changes", key=f"save_changes_{idx}"):
                                # データの更新
                                manual_data.at[idx, 'question'] = edited_question
                                manual_data.at[idx, 'answer'] = edited_answer
                                manual_data.at[idx, 'priority'] = edited_priority
                                # セッションステートとファイルに保存
                                st.session_state['manual_data'] = manual_data
                                manual_data.to_csv('manual.csv', index=False, encoding='utf-8')
                                st.success(f"Q&A {idx + 1} has been updated.")
                                # Google Drive にアップロード
                                upload_file_to_drive(drive_service, 'manual.csv', folder_id)
                        with col2:
                            if st.button("Delete Q&A", key=f"delete_qna_{idx}"):
                                manual_data = manual_data.drop(idx).reset_index(drop=True)
                                st.session_state['manual_data'] = manual_data
                                manual_data.to_csv('manual.csv', index=False, encoding='utf-8')
                                st.success(f"Q&A {idx + 1} has been deleted.")
                                # Google Drive にアップロード
                                upload_file_to_drive(drive_service, 'manual.csv', folder_id)
        else:
            st.info("No Q&A entries found in manual.csv.")

        # ---------------------------
        # Manage Feedback.csv
        # ---------------------------
        st.markdown("## 🗑️ Manage Feedback")

        feedback_data = st.session_state['feedback_data']
        if not feedback_data.empty:
            for idx, row in feedback_data.iterrows():
                # 各フィードバックエントリに「Delete」ボタンを追加
                cols = st.columns([8, 2])  # データとボタンの割合を調整
                with cols[0]:
                    st.markdown(f"**Feedback {idx + 1}:**")
                    st.markdown(f"**Question:** {row['question']}")
                    st.markdown(f"**Answer:** {row['answer']}")
                    st.markdown(f"**Feedback:** {row['feedback']}")
                with cols[1]:
                    delete_feedback_button = st.button("Delete", key=f"delete_feedback_button_{idx}")

                if delete_feedback_button:
                    feedback_data = feedback_data.drop(idx).reset_index(drop=True)
                    st.session_state['feedback_data'] = feedback_data
                    feedback_data.to_csv('feedback.csv', index=False, encoding='utf-8')
                    st.success(f"Feedback {idx + 1} has been deleted.")
                    # Google Drive にアップロード
                    upload_file_to_drive(drive_service, 'feedback.csv', folder_id)
        else:
            st.info("There is no feedback to display.")

        # ---------------------------
        # Display Current Manual Data (DataFrame View) with Edit Buttons
        # ---------------------------
        st.markdown("## 📄 Current Manual Data (DataFrame View)")
        if not st.session_state['manual_data'].empty:
            st.dataframe(st.session_state['manual_data'])
        else:
            st.info("No data in manual.csv.")

        # ---------------------------
        # Display Current Feedback Data
        # ---------------------------
        st.markdown("## 📊 All Feedback")
        if not st.session_state['feedback_data'].empty:
            st.dataframe(st.session_state['feedback_data'])
            positive_feedback = st.session_state['feedback_data'][st.session_state['feedback_data']['feedback'] == 'Yes'].shape[0]
            negative_feedback = st.session_state['feedback_data'][st.session_state['feedback_data']['feedback'] == 'No'].shape[0]
            st.markdown(f"**Helpful:** {positive_feedback}")
            st.markdown(f"**Not Helpful:** {negative_feedback}")
        else:
            st.warning("There is no feedback yet.")

        # ---------------------------
        # Download Files
        # ---------------------------
        st.markdown("## 📥 Download Data Files")
        if os.path.exists('manual.csv'):
            try:
                with open('manual.csv', 'rb') as f:
                    st.download_button('Download manual.csv', f, file_name='manual.csv')
            except Exception as e:
                st.error(f"Failed to read manual.csv for download: {e}")
        if os.path.exists('feedback.csv'):
            try:
                with open('feedback.csv', 'rb') as f:
                    st.download_button('Download feedback.csv', f, file_name='feedback.csv')
            except Exception as e:
                st.error(f"Failed to read feedback.csv for download: {e}")
    else:
        st.error("Incorrect password.")
