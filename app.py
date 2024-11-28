import streamlit as st
import openai
import pandas as pd
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# -------------------------------
# Google Drive 認証
# -------------------------------
def authenticate_google_drive():
    """
    サービスアカウントの資格情報を使用してGoogle Driveに認証し、サービスオブジェクトを返す関数
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

# Google DriveフォルダID
FOLDER_ID = '1ifXllfufA5EVGlWVEk8RAYvrQKE-5Ox9'  # 実際のフォルダIDに置き換えてください

# -------------------------------
# ファイルアップロード関数
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
        # 既存のファイルがあるか確認
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
# OpenAI APIキー設定
# -------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------
# データロード関数
# -------------------------------
def load_faq_data(file_path='faq.csv'):
    """
    faq.csv からFAQデータをロードし、優先順位でソートしたリストを返す関数
    """
    if os.path.exists(file_path):
        try:
            data = pd.read_csv(file_path, encoding='utf-8')
            data_sorted = data.sort_values(by='priority')
            faq_list = data_sorted.to_dict(orient='records')
            return faq_list
        except Exception as e:
            st.error(f"Failed to load FAQ data: {e}")
            return []
    else:
        st.warning("faq.csv not found. Please add FAQs via the admin page.")
        return []

def load_manual_data(file_path='manual.csv'):
    """
    manual.csv からマニュアルデータをロードする関数
    """
    if os.path.exists(file_path):
        try:
            data = pd.read_csv(file_path, encoding='utf-8')
            manual_list = data.to_dict(orient='records')
            return manual_list
        except Exception as e:
            st.error(f"Failed to load manual data: {e}")
            return []
    else:
        st.warning("manual.csv not found. Please add manual entries via the admin page.")
        return []

def load_questions_data(file_path='questions.csv'):
    """
    questions.csv からユーザーの質問とフィードバックをロードする関数
    """
    if os.path.exists(file_path):
        try:
            data = pd.read_csv(file_path, encoding='utf-8')
            return data
        except pd.errors.EmptyDataError:
            st.warning("questions.csv is empty.")
            return pd.DataFrame(columns=['question', 'answer', 'feedback'])
        except Exception as e:
            st.error(f"Failed to load questions data: {e}")
            return pd.DataFrame(columns=['question', 'answer', 'feedback'])
    else:
        st.warning("questions.csv not found.")
        return pd.DataFrame(columns=['question', 'answer', 'feedback'])

# -------------------------------
# データ保存関数
# -------------------------------
def save_faq_data(faq_df, file_path='faq.csv'):
    """
    FAQデータフレームをfaq.csvに保存し、Google Driveにアップロードする関数
    """
    try:
        faq_df.to_csv(file_path, index=False, encoding='utf-8')
        upload_file_to_drive(drive_service, file_path, FOLDER_ID)
        st.success("FAQ data saved successfully.")
    except Exception as e:
        st.error(f"Failed to save FAQ data: {e}")

def save_manual_data(manual_df, file_path='manual.csv'):
    """
    Manualデータフレームをmanual.csvに保存し、Google Driveにアップロードする関数
    """
    try:
        manual_df.to_csv(file_path, index=False, encoding='utf-8')
        upload_file_to_drive(drive_service, file_path, FOLDER_ID)
        st.success("Manual data saved successfully.")
    except Exception as e:
        st.error(f"Failed to save manual data: {e}")

def save_questions_data(questions_df, file_path='questions.csv'):
    """
    Questionsデータフレームをquestions.csvに保存し、Google Driveにアップロードする関数
    """
    try:
        questions_df.to_csv(file_path, index=False, encoding='utf-8')
        upload_file_to_drive(drive_service, file_path, FOLDER_ID)
        st.success("Questions data saved successfully.")
    except Exception as e:
        st.error(f"Failed to save questions data: {e}")

# -------------------------------
# セッションステートの初期化
# -------------------------------
if 'faq_list' not in st.session_state:
    st.session_state['faq_list'] = load_faq_data()
if 'manual_list' not in st.session_state:
    st.session_state['manual_list'] = load_manual_data()
if 'questions_df' not in st.session_state:
    st.session_state['questions_df'] = load_questions_data()
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'admin_faq_df' not in st.session_state:
    st.session_state['admin_faq_df'] = pd.DataFrame(load_faq_data())
if 'admin_manual_df' not in st.session_state:
    st.session_state['admin_manual_df'] = pd.DataFrame(load_manual_data())

# -------------------------------
# カスタムCSSによるスタイリング
# -------------------------------
st.markdown(
    """
    <style>
    /* タイトルやテキストの色 */
    h1, h2, h3, h4, h5, h6 {
        color: #333333;
    }
    /* サイドバーのスタイル */
    .css-1d391kg {
        background-color: #ffffff;
    }
    .css-1d391kg .css-hxt7ib {
        color: #333333;
    }
    /* 入力フィールドのスタイル */
    .stTextInput > div > div > input, .stTextArea textarea {
        background-color: #ffffff;
        color: #333333;
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
        background-color: #ffffff;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        color: #333333;
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
        color: #333333;
    }
    .stRadio>div>label {
        margin-right: 10px;
    }
    /* データフレームのスタイル */
    .stDataFrame {
        margin-top: 20px;
        color: #333333;
    }
    /* FAQセクションのスタイル */
    .faq-container {
        display: flex;
        overflow-x: auto;
        padding: 10px 0;
    }
    .faq-item {
        background-color: #0066cc;
        color: #FFFFFF;
        padding: 20px;
        margin-right: 15px;
        border-radius: 50%;
        min-width: 150px;
        height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        text-align: center;
        transition: background-color 0.3s;
        white-space: normal;
    }
    .faq-item:hover {
        background-color: #0052a3;
    }
    /* スクロールバーのスタイル */
    .faq-container::-webkit-scrollbar {
        height: 8px;
    }
    .faq-container::-webkit-scrollbar-thumb {
        background-color: #cccccc;
        border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# ヘルパー関数
# -------------------------------
def get_combined_faq_manual(faq_list, manual_list):
    """
    FAQリストを優先し、マニュアルリストを続けて結合したリストを返す関数
    """
    return faq_list + manual_list

def display_faq_section(faq_list, manual_list):
    """
    FAQとマニュアルの質問を横スクロール可能な丸囲みで表示する関数
    最初に3つのFAQを表示し、残りはスクロールで表示
    """
    st.markdown("## ❓ Frequently Asked Questions")
    
    combined_list = get_combined_faq_manual(faq_list, manual_list)
    
    # 最初の3つを表示
    initial_faq = combined_list[:3]
    remaining_faq = combined_list[3:]
    
    # 最初の3つを表示
    st.markdown('<div class="faq-container">', unsafe_allow_html=True)
    for faq in initial_faq:
        st.markdown(
            f'''
            <div class="faq-item" style="flex: 0 0 auto;">
                <button style="background: none; border: none; color: inherit; cursor: pointer; width: 100%; height: 100%;" 
                        onclick="window.location.href='#';">
                    ❓<br>{faq['question']}
                </button>
            </div>
            ''',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 残りのFAQをスクロール可能なセクションで表示
    if remaining_faq:
        st.markdown('<div class="faq-container">', unsafe_allow_html=True)
        for faq in remaining_faq:
            st.markdown(
                f'''
                <div class="faq-item" style="flex: 0 0 auto;">
                    <button style="background: none; border: none; color: inherit; cursor: pointer; width: 100%; height: 100%;" 
                            onclick="window.location.href='#';">
                        ❓<br>{faq['question']}
                    </button>
                </div>
                ''',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------
# ユーザーページ
# -------------------------------
def user_page():
    # アプリのタイトルと説明
    st.title("💬 Q&A Bot")
    st.write("This bot answers your questions based on the manual and FAQs. Please enter your question below.")
    
    # ベータ版の通知
    st.markdown(
        """
        <div style='background-color: #f2f2f2; padding: 10px; border-radius: 5px; margin-bottom: 20px;'>
            <span style='color: #333333; font-size: 16px;'>
                <strong>This is a beta version. Your active feedback would be greatly appreciated!</strong>
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # -------------------------------
    # FAQセクションの表示
    # -------------------------------
    combined_faq_list = get_combined_faq_manual(st.session_state['faq_list'], st.session_state['manual_list'])
    display_faq_section(st.session_state['faq_list'], st.session_state['manual_list'])
    
    # -------------------------------
    # FAQボタンの表示と処理
    # -------------------------------
    combined_faq_list = get_combined_faq_manual(st.session_state['faq_list'], st.session_state['manual_list'])
    
    # 初期の3つを表示
    initial_faq = combined_faq_list[:3]
    remaining_faq = combined_faq_list[3:]
    
    # 最初の3つのFAQボタン
    st.markdown('<div class="faq-container">', unsafe_allow_html=True)
    for faq in initial_faq:
        if st.button(faq['question'], key=f"faq_{faq['priority']}_{faq['question']}"):
            st.session_state['question_input'] = faq['question']
            process_question(faq['question'])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 残りのFAQボタンをスクロール可能なセクションで表示
    if remaining_faq:
        st.markdown('<div class="faq-container">', unsafe_allow_html=True)
        for faq in remaining_faq:
            if st.button(faq['question'], key=f"faq_{faq['priority']}_{faq['question']}"):
                st.session_state['question_input'] = faq['question']
                process_question(faq['question'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    # -------------------------------
    # ユーザーの質問入力
    # -------------------------------
    question = st.text_input("Enter your question:", key="question_input")
    
    if st.button("Submit", key='submit_button'):
        if question:
            process_question(question)
        else:
            st.warning("Please enter a question.")

    # -------------------------------
    # 質問処理関数
    # -------------------------------
    def process_question(user_question):
        """
        ユーザーの質問を処理し、回答を取得して表示する関数
        """
        # FAQとマニュアルの内容を結合
        manual_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in combined_faq_list])
        
        # OpenAI APIを呼び出して回答を取得
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant who answers the user's questions based solely on the provided manual and FAQs."
                            " Please answer in the same language as the user's question."
                            " Do not provide information not included in the manual or FAQs, but use the knowledge from them to answer flexibly."
                        )
                    },
                    {"role": "user", "content": f"Manual and FAQs:\n{manual_text}\n\nUser's question:\n{user_question}"}
                ]
            )
            ai_response = response['choices'][0]['message']['content']
            st.success("The answer has been generated. Please see below.")
            
            # 質問と回答を表示
            st.markdown(f"<div class='question'><strong>Question:</strong> {user_question}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='answer'><strong>Answer:</strong> {ai_response}</div>", unsafe_allow_html=True)
            
            # 履歴に追加
            st.session_state['history'].append({'question': user_question, 'answer': ai_response, 'feedback': "Not Rated"})
            
            # questions.csvに保存
            def save_question():
                questions_df = st.session_state['questions_df']
                new_row = {
                    'question': user_question,
                    'answer': ai_response,
                    'feedback': "Not Rated"
                }
                # append を concat に置き換え
                questions_df = pd.concat([questions_df, pd.DataFrame([new_row])], ignore_index=True)
                st.session_state['questions_df'] = questions_df
                save_questions_data(questions_df)
            
            save_question()
            
        except openai.error.OpenAIError as e:
            st.error(f"An error occurred while contacting OpenAI: {e}")
    
    # -------------------------------
    # 質問履歴とフィードバック
    # -------------------------------
    st.markdown("## 🕘 Question History")
    for idx, qa in enumerate(reversed(st.session_state['history'])):
        actual_idx = len(st.session_state['history']) - idx - 1
        st.markdown(f"<div class='question'><strong>Question {actual_idx+1}:</strong> {qa['question']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='answer'><strong>Answer {actual_idx+1}:</strong> {qa['answer']}</div>", unsafe_allow_html=True)
        
        if qa['feedback'] == "Not Rated":
            with st.container():
                feedback = st.radio(
                    "Was this answer helpful?",
                    ["Yes", "No"],
                    key=f"feedback_{actual_idx}",
                    horizontal=True
                )
                if st.button("Submit Feedback", key=f"submit_feedback_{actual_idx}"):
                    st.session_state['history'][actual_idx]['feedback'] = feedback
                    st.success("Thank you for your feedback!")
                    
                    # questions.csvのフィードバックを更新
                    questions_df = st.session_state['questions_df']
                    mask = (questions_df['question'] == qa['question']) & (questions_df['answer'] == qa['answer'])
                    questions_df.loc[mask, 'feedback'] = feedback
                    st.session_state['questions_df'] = questions_df
                    save_questions_data(questions_df)
        else:
            st.markdown(f"**Feedback {actual_idx+1}:** {qa['feedback']}")

# -------------------------------
# 管理者ページ
# -------------------------------
def admin_page():
    # 管理者認証
    admin_password = st.sidebar.text_input("Enter the password", type="password")
    stored_admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not stored_admin_password:
        st.error("ADMIN_PASSWORD environment variable is not set.")
        return
    elif admin_password != stored_admin_password:
        st.error("Incorrect password.")
        return
    
    st.success("Accessed the admin page.")
    
    # -------------------------------
    # FAQ管理
    # -------------------------------
    st.markdown("## ➕ Admin: Manage FAQs")
    
    with st.expander("Add FAQ"):
        new_faq_question = st.text_input("New Question")
        new_faq_answer = st.text_area("New Answer")
        new_faq_priority = st.number_input("Priority (Lower number = Higher priority)", min_value=1, step=1, value=1)
        if st.button("Add FAQ"):
            if new_faq_question and new_faq_answer:
                new_faq = {'priority': new_faq_priority, 'question': new_faq_question, 'answer': new_faq_answer}
                # append を concat に置き換え
                st.session_state['admin_faq_df'] = pd.concat([st.session_state['admin_faq_df'], pd.DataFrame([new_faq])], ignore_index=True)
                save_faq_data(st.session_state['admin_faq_df'])
                st.experimental_rerun()
            else:
                st.warning("Please enter both a question and an answer.")
    
    with st.expander("Edit/Delete FAQs"):
        if not st.session_state['admin_faq_df'].empty:
            faq_df = st.session_state['admin_faq_df']
            for idx, row in faq_df.iterrows():
                st.markdown(f"### FAQ {idx + 1}")
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    edited_question = st.text_input("Question", value=row['question'], key=f"admin_faq_question_{idx}")
                with col2:
                    edited_answer = st.text_area("Answer", value=row['answer'], key=f"admin_faq_answer_{idx}")
                with col3:
                    edited_priority = st.number_input("Priority", min_value=1, step=1, value=row['priority'], key=f"admin_faq_priority_{idx}")
                
                # Update and Delete buttons
                update_col, delete_col = st.columns([1, 1])
                with update_col:
                    if st.button("Update", key=f"update_faq_{idx}"):
                        st.session_state['admin_faq_df'].at[idx, 'question'] = edited_question
                        st.session_state['admin_faq_df'].at[idx, 'answer'] = edited_answer
                        st.session_state['admin_faq_df'].at[idx, 'priority'] = edited_priority
                        save_faq_data(st.session_state['admin_faq_df'])
                        st.experimental_rerun()
                with delete_col:
                    if st.button("Delete", key=f"delete_faq_{idx}"):
                        st.session_state['admin_faq_df'] = st.session_state['admin_faq_df'].drop(idx).reset_index(drop=True)
                        save_faq_data(st.session_state['admin_faq_df'])
                        st.experimental_rerun()
        else:
            st.warning("No FAQs available.")
    
    # -------------------------------
    # Manual管理
    # -------------------------------
    st.markdown("## ➕ Admin: Manage Manual")
    
    with st.expander("Add Manual"):
        new_manual_question = st.text_input("New Manual Question")
        new_manual_answer = st.text_area("New Manual Answer")
        if st.button("Add Manual"):
            if new_manual_question and new_manual_answer:
                new_manual = {'question': new_manual_question, 'answer': new_manual_answer}
                # append を concat に置き換え
                st.session_state['admin_manual_df'] = pd.concat([st.session_state['admin_manual_df'], pd.DataFrame([new_manual])], ignore_index=True)
                save_manual_data(st.session_state['admin_manual_df'])
                st.experimental_rerun()
            else:
                st.warning("Please enter both a question and an answer.")
    
    with st.expander("Edit/Delete Manual Entries"):
        if not st.session_state['admin_manual_df'].empty:
            manual_df = st.session_state['admin_manual_df']
            for idx, row in manual_df.iterrows():
                st.markdown(f"### Manual {idx + 1}")
                col1, col2 = st.columns([2, 2])
                with col1:
                    edited_manual_question = st.text_input("Question", value=row['question'], key=f"admin_manual_question_{idx}")
                with col2:
                    edited_manual_answer = st.text_area("Answer", value=row['answer'], key=f"admin_manual_answer_{idx}")
                
                # Update and Delete buttons
                update_col, delete_col = st.columns([1, 1])
                with update_col:
                    if st.button("Update", key=f"update_manual_{idx}"):
                        st.session_state['admin_manual_df'].at[idx, 'question'] = edited_manual_question
                        st.session_state['admin_manual_df'].at[idx, 'answer'] = edited_manual_answer
                        save_manual_data(st.session_state['admin_manual_df'])
                        st.experimental_rerun()
                with delete_col:
                    if st.button("Delete", key=f"delete_manual_{idx}"):
                        st.session_state['admin_manual_df'] = st.session_state['admin_manual_df'].drop(idx).reset_index(drop=True)
                        save_manual_data(st.session_state['admin_manual_df'])
                        st.experimental_rerun()
        else:
            st.warning("No Manual entries available.")
    
    # -------------------------------
    # フィードバック管理
    # -------------------------------
    st.markdown("## ➕ Admin: Manage Feedback")
    
    with st.expander("Delete Feedback"):
        if not st.session_state['questions_df'].empty:
            questions_df = st.session_state['questions_df']
            for idx, row in questions_df.iterrows():
                st.markdown(f"### Feedback {idx + 1}")
                st.markdown(f"**Question:** {row['question']}")
                st.markdown(f"**Answer:** {row['answer']}")
                st.markdown(f"**Feedback:** {row['feedback']}")
                if st.button("Delete Feedback", key=f"delete_feedback_{idx}"):
                    st.session_state['questions_df'] = st.session_state['questions_df'].drop(idx).reset_index(drop=True)
                    save_questions_data(st.session_state['questions_df'])
                    st.experimental_rerun()
        else:
            st.warning("No feedback data available.")
    
    # -------------------------------
    # 現在のデータの表示
    # -------------------------------
    st.markdown("## 📄 Current FAQs")
    if not st.session_state['admin_faq_df'].empty:
        st.dataframe(st.session_state['admin_faq_df'])
    else:
        st.warning("No FAQ data available.")
    
    st.markdown("## 📄 Current Manual")
    if not st.session_state['admin_manual_df'].empty:
        st.dataframe(st.session_state['admin_manual_df'])
    else:
        st.warning("No Manual data available.")
    
    st.markdown("## 📊 All Questions and Feedback")
    if not st.session_state['questions_df'].empty:
        st.dataframe(st.session_state['questions_df'])
        positive_feedback = st.session_state['questions_df'][st.session_state['questions_df']['feedback'] == 'Yes'].shape[0]
        negative_feedback = st.session_state['questions_df'][st.session_state['questions_df']['feedback'] == 'No'].shape[0]
        st.markdown(f"**Helpful:** {positive_feedback}")
        st.markdown(f"**Not Helpful:** {negative_feedback}")
    else:
        st.warning("No questions and feedback data available.")
    
    # -------------------------------
    # データファイルのダウンロード
    # -------------------------------
    st.markdown("## 📥 Download Data Files")
    
    with st.expander("Download Data"):
        if os.path.exists('faq.csv'):
            try:
                with open('faq.csv', 'rb') as f:
                    st.download_button('Download FAQ Data', f, file_name='faq.csv')
            except Exception as e:
                st.error(f"Failed to read faq.csv for download: {e}")
        if os.path.exists('manual.csv'):
            try:
                with open('manual.csv', 'rb') as f:
                    st.download_button('Download Manual Data', f, file_name='manual.csv')
            except Exception as e:
                st.error(f"Failed to read manual.csv for download: {e}")
        if os.path.exists('questions.csv'):
            try:
                with open('questions.csv', 'rb') as f:
                    st.download_button('Download Questions Data', f, file_name='questions.csv')
            except Exception as e:
                st.error(f"Failed to read questions.csv for download: {e}")

# -------------------------------
# ページ選択
# -------------------------------
page = st.sidebar.selectbox(
    "Select a page",
    ["User", "Admin"],
    index=0,
    key='page_selection'
)

# -------------------------------
# 選択されたページの表示
# -------------------------------
if page == "User":
    user_page()
elif page == "Admin":
    admin_page()
