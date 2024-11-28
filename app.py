import streamlit as st
import openai
import pandas as pd
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# -------------------------------
# Google Drive Authentication
# -------------------------------
def authenticate_google_drive():
    """
    Authenticates with Google Drive using service account credentials and returns the service object.
    """
    credentials_json = os.getenv("GDRIVE_CREDENTIALS")
    if not credentials_json:
        raise ValueError("GDRIVE_CREDENTIALS environment variable is not set.")
    
    try:
        service_account_info = json.loads(credentials_json)
    except json.JSONDecodeError:
        raise ValueError("GDRIVE_CREDENTIALS environment variable contains invalid JSON.")
    
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    
    service = build('drive', 'v3', credentials=credentials)
    return service

# Authenticate with Google Drive
try:
    drive_service = authenticate_google_drive()
except Exception as e:
    st.error(f"Google Drive authentication failed: {e}")

# Google Drive Folder ID
FOLDER_ID = '1ifXllfufA5EVGlWVEk8RAYvrQKE-5Ox9'  # Replace with your actual folder ID

# -------------------------------
# File Upload Function
# -------------------------------
def upload_file_to_drive(service, file_path, folder_id):
    """
    Uploads or updates a file to the specified Google Drive folder.
    """
    file_name = os.path.basename(file_path)
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    try:
        # Check if the file already exists
        existing_files = service.files().list(
            q=f"name='{file_name}' and '{folder_id}' in parents and trashed=false",
            fields='files(id, name)'
        ).execute()
        if existing_files['files']:
            # Update existing file
            file_id = existing_files['files'][0]['id']
            service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            st.write(f'Updated {file_name} in Google Drive.')
        else:
            # Upload new file
            service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            st.write(f'Uploaded {file_name} to Google Drive.')
    except Exception as e:
        st.error(f"Failed to upload {file_name} to Google Drive: {e}")

# -------------------------------
# OpenAI API Key Configuration
# -------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------
# Data Loading Functions
# -------------------------------
def load_manual_data(file_path='manual.csv'):
    """
    Loads manual data from manual.csv and returns a list of dictionaries sorted by priority.
    """
    if os.path.exists(file_path):
        try:
            data = pd.read_csv(file_path, encoding='utf-8')
            data_sorted = data.sort_values(by='priority')
            manual_list = data_sorted.to_dict(orient='records')
            return manual_list
        except Exception as e:
            st.error(f"Failed to load manual data: {e}")
            return []
    else:
        st.warning("manual.csv not found. Please add manual entries via the admin page.")
        return []

def load_questions_data(file_path='questions.csv'):
    """
    Loads user questions and feedback from questions.csv and returns a DataFrame.
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
# Data Saving Functions
# -------------------------------
def save_manual_data(manual_df, file_path='manual.csv'):
    """
    Saves the manual DataFrame to manual.csv and uploads it to Google Drive.
    """
    try:
        manual_df.to_csv(file_path, index=False, encoding='utf-8')
        upload_file_to_drive(drive_service, file_path, FOLDER_ID)
        st.success("Manual data saved successfully.")
    except Exception as e:
        st.error(f"Failed to save manual data: {e}")

def save_questions_data(questions_df, file_path='questions.csv'):
    """
    Saves the questions DataFrame to questions.csv and uploads it to Google Drive.
    """
    try:
        questions_df.to_csv(file_path, index=False, encoding='utf-8')
        upload_file_to_drive(drive_service, file_path, FOLDER_ID)
        # Avoid multiple success messages by commenting out
        # st.success("Questions data saved successfully.")
    except Exception as e:
        st.error(f"Failed to save questions data: {e}")

# -------------------------------
# Initialize Session State
# -------------------------------
if 'manual_list' not in st.session_state:
    st.session_state['manual_list'] = load_manual_data()
if 'questions_df' not in st.session_state:
    st.session_state['questions_df'] = load_questions_data()
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'admin_manual_df' not in st.session_state:
    st.session_state['admin_manual_df'] = pd.DataFrame(load_manual_data())

# -------------------------------
# Custom CSS Styling
# -------------------------------
st.markdown(
    """
    <style>
    /* Overall background color */
    .stApp {
        background-color: #000000;
        font-family: 'Helvetica Neue', sans-serif;
    }
    /* Title and text color */
    h1, h2, h3, h4, h5, h6, p, label {
        color: #FFFFFF;
    }
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #1a1a1a;
    }
    .css-1d391kg .css-hxt7ib {
        color: #FFFFFF;
    }
    /* Input fields styling */
    .stTextInput > div > div > input, .stTextArea textarea {
        background-color: #333333;
        color: #FFFFFF;
    }
    /* Button styling */
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
    /* Question and Answer styling */
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
    /* Feedback section styling */
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
    /* DataFrame styling */
    .stDataFrame {
        margin-top: 20px;
        color: #FFFFFF;
    }
    /* FAQ section styling */
    .faq-container {
        display: flex;
        overflow-x: auto;
        padding: 10px 0;
    }
    .faq-item {
        background-color: #0066cc;
        color: #FFFFFF;
        padding: 15px;
        margin-right: 10px;
        border-radius: 50%;
        width: 120px;
        height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        text-align: center;
        transition: background-color 0.3s;
        white-space: normal;
    }
    .faq-item:hover {
        background-color: #333333;
    }
    /* Scrollbar styling */
    .faq-container::-webkit-scrollbar {
        height: 8px;
    }
    .faq-container::-webkit-scrollbar-thumb {
        background-color: #555555;
        border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# Helper Functions
# -------------------------------
def get_combined_manual(manual_list):
    """
    Returns the manual list sorted by priority.
    """
    return manual_list

def display_faq_section(manual_list):
    """
    Displays FAQs in a horizontally scrollable, circular layout.
    Initially shows 3 FAQs, with the rest accessible via scrolling.
    Clicking a FAQ sets the question input.
    """
    st.markdown("## ❓ Frequently Asked Questions")
    
    combined_list = get_combined_manual(manual_list)
    
    # Display the first 3 FAQs
    initial_faq = combined_list[:3]
    remaining_faq = combined_list[3:]
    
    # Function to handle FAQ button clicks
    def handle_faq_click(faq_question):
        st.session_state['question_input'] = faq_question
    
    # Display initial FAQs
    st.markdown('<div class="faq-container">', unsafe_allow_html=True)
    for faq in initial_faq:
        st.markdown(
            f'''
            <div class="faq-item">
                <button style="background: none; border: none; color: inherit; cursor: pointer; width: 100%; height: 100%;" 
                        onclick="window.parent.postMessage({{func: 'set_question', question: '{faq['question']}' }}, '*')">
                    ❓<br>{faq['question']}
                </button>
            </div>
            ''',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Display remaining FAQs
    if remaining_faq:
        st.markdown('<div class="faq-container">', unsafe_allow_html=True)
        for faq in remaining_faq:
            st.markdown(
                f'''
                <div class="faq-item">
                    <button style="background: none; border: none; color: inherit; cursor: pointer; width: 100%; height: 100%;" 
                            onclick="window.parent.postMessage({{func: 'set_question', question: '{faq['question']}' }}, '*')">
                        ❓<br>{faq['question']}
                    </button>
                </div>
                ''',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # Handle messages from buttons (JavaScript workaround)
    query = st.experimental_get_query_params()
    if 'question' in st.session_state:
        pass  # The question is already set
    else:
        # Use a hidden iframe or another method to capture postMessage
        # However, Streamlit does not support this directly
        # Therefore, we'll use a workaround with buttons below
        pass

# -------------------------------
# User Page
# -------------------------------
def user_page():
    # App title and description
    st.title("💬 Q&A Bot")
    st.write("This bot answers your questions based on the manual. Please enter your question below or select a frequently asked question.")

    # Beta version notice
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

    # -------------------------------
    # FAQ Section
    # -------------------------------
    display_faq_section(st.session_state['manual_list'])

    # -------------------------------
    # User Question Input
    # -------------------------------
    question = st.text_input("Enter your question:", key="question_input")

    if st.button("Submit", key='submit_button'):
        if question:
            process_question(question)
        else:
            st.warning("Please enter a question.")

    # -------------------------------
    # Question Processing Function
    # -------------------------------
    def process_question(user_question):
        """
        Processes the user's question, retrieves an answer from OpenAI, and updates the history and CSV.
        """
        combined_manual = get_combined_manual(st.session_state['manual_list'])
        manual_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in combined_manual])
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant who answers the user's questions based solely on the provided manual."
                            " Please answer in the same language as the user's question."
                            " Do not provide information not included in the manual, but use the knowledge from it to answer flexibly."
                        )
                    },
                    {"role": "user", "content": f"Manual:\n{manual_text}\n\nUser's question:\n{user_question}"}
                ]
            )
            ai_response = response['choices'][0]['message']['content']
            st.success("The answer has been generated. Please see below.")
            
            # Display question and answer
            st.markdown(f"<div class='question'><strong>Question:</strong> {user_question}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='answer'><strong>Answer:</strong> {ai_response}</div>", unsafe_allow_html=True)
            
            # Append to history
            st.session_state['history'].append({'question': user_question, 'answer': ai_response, 'feedback': "Not Rated"})
            
            # Save to questions.csv
            new_row = {
                'question': user_question,
                'answer': ai_response,
                'feedback': "Not Rated"
            }
            questions_df = st.session_state['questions_df']
            questions_df = pd.concat([questions_df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state['questions_df'] = questions_df
            save_questions_data(questions_df)
            
        except openai.error.OpenAIError as e:
            st.error(f"An error occurred while contacting OpenAI: {e}")

    # -------------------------------
    # Question History and Feedback
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
                    
                    # Update feedback in questions.csv
                    questions_df = st.session_state['questions_df']
                    mask = (questions_df['question'] == qa['question']) & (questions_df['answer'] == qa['answer'])
                    questions_df.loc[mask, 'feedback'] = feedback
                    st.session_state['questions_df'] = questions_df
                    save_questions_data(questions_df)
        else:
            st.markdown(f"**Feedback {actual_idx+1}:** {qa['feedback']}")

# -------------------------------
# Admin Page
# -------------------------------
def admin_page():
    # Admin Authentication
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
    # Manual Management
    # -------------------------------
    st.markdown("## ➕ Admin: Manage Manual")
    
    with st.expander("Add Manual"):
        new_manual_question = st.text_input("New Manual Question")
        new_manual_answer = st.text_area("New Manual Answer")
        if st.button("Add Manual"):
            if new_manual_question and new_manual_answer:
                new_manual = {'question': new_manual_question, 'answer': new_manual_answer}
                # Use concat instead of append
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
    # Feedback Management
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
    # Display Current Data
    # -------------------------------
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
    # Download Data Files
    # -------------------------------
    st.markdown("## 📥 Download Data Files")
    
    with st.expander("Download Data"):
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
# Page Selection
# -------------------------------
page = st.sidebar.selectbox(
    "Select a page",
    ["User", "Admin"],
    index=0,
    key='page_selection'
)

# -------------------------------
# Display Selected Page
# -------------------------------
if page == "User":
    user_page()
elif page == "Admin":
    admin_page()
