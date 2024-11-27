import streamlit as st
import openai
import pandas as pd
import os

# OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Apply custom CSS for styling
st.markdown(
    """
    <style>
    /* Overall background color */
    .stApp {
        background-color: #000000;
        font-family: 'Helvetica Neue', sans-serif;
    }
    /* Title style */
    h1 {
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 20px;
    }
    /* Sidebar style */
    .css-1d391kg {
        background-color: #1a1a1a;
    }
    .css-1d391kg .css-hxt7ib {
        color: #FFFFFF;
    }
    /* Input field style */
    .stTextInput, .stTextArea {
        margin-bottom: 20px;
    }
    .stTextInput>div>div>input, .stTextArea textarea {
        background-color: #333333;
        color: #FFFFFF;
    }
    /* Button style */
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
    /* Question and answer style */
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
    /* Feedback style */
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
    /* Dataframe style */
    .stDataFrame {
        margin-top: 20px;
        color: #FFFFFF;
    }
    /* Adjust text color globally */
    .css-1e5imcs, .css-1v3fvcr {
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Load manual data
def load_manual():
    if os.path.exists('manual.csv'):
        try:
            data = pd.read_csv('manual.csv', encoding='utf-8')
            if data.empty:
                st.error("The manual.csv file is empty. Please add data.")
                return pd.DataFrame(columns=['Question', 'Answer'])
            return data
        except pd.errors.EmptyDataError:
            st.error("The manual.csv file has no data.")
            return pd.DataFrame(columns=['Question', 'Answer'])
        except Exception as e:
            st.error(f"An error occurred while loading manual.csv: {e}")
            return pd.DataFrame(columns=['Question', 'Answer'])
    else:
        st.error("The manual.csv file was not found.")
        return pd.DataFrame(columns=['Question', 'Answer'])

manual_data = load_manual()

# Store manual_data in session state
if 'manual_data' not in st.session_state:
    st.session_state['manual_data'] = manual_data
else:
    manual_data = st.session_state['manual_data']

# Initialize session state for history
if 'history' not in st.session_state:
    st.session_state['history'] = []

# Page selection in the sidebar
page = st.sidebar.selectbox(
    "Select a page",
    ["User", "Admin"],
    index=0,
    key='page_selection'
)

if page == "User":
    # App configuration
    st.title("💬 Q&A Bot")
    st.write("This bot answers your questions based on the manual. Please enter your question below.")
    st.write("**This is a beta version. Your active feedback would be greatly appreciated! by Koki**")

    question = st.text_input("Enter your question:")

    if st.button("Submit"):
        if question:
            # Concatenate manual content into text
            manual_text = "\n".join(manual_data['質問'] + "\n" + manual_data['回答'])

            # Send question and manual to OpenAI to get the answer
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

                # Display question and answer
                st.markdown(f"<div class='question'><strong>Question:</strong> {question}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='answer'><strong>Answer:</strong> {ai_response}</div>", unsafe_allow_html=True)

                # Add question and answer to history
                st.session_state['history'].append({'question': question, 'answer': ai_response, 'feedback': "Not Rated"})

                # Save question and answer to 'questions.csv'
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

                save_question()

            except openai.error.OpenAIError as e:
                st.error(f"An error occurred while contacting OpenAI: {e}")
        else:
            st.warning("Please enter a question.")

    # Display question history with the newest first
    st.markdown("## 🕘 Question History")
    for idx, qa in enumerate(reversed(st.session_state['history'])):
        actual_idx = len(st.session_state['history']) - idx - 1
        st.markdown(f"<div class='question'><strong>Question {actual_idx+1}:</strong> {qa['question']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='answer'><strong>Answer {actual_idx+1}:</strong> {qa['answer']}</div>", unsafe_allow_html=True)

        if qa['feedback'] == "Not Rated":
            # Move feedback section directly under the answer
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

                # Update feedback in 'questions.csv'
                if os.path.exists('questions.csv'):
                    question_data = pd.read_csv('questions.csv', encoding='utf-8')
                    mask = (question_data['question'] == qa['question']) & (question_data['answer'] == qa['answer'])
                    question_data.loc[mask, 'feedback'] = feedback
                    question_data.to_csv('questions.csv', index=False, encoding='utf-8')
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"**Feedback {actual_idx+1}:** {qa['feedback']}")

elif page == "Admin":
    # Admin authentication
    admin_password = st.sidebar.text_input("Enter the password", type="password")
    if admin_password == "こうき": 
        st.success("Accessed the admin page.")

        # Function to clear inputs
        def clear_inputs():
            st.session_state["new_question_value"] = ""
            st.session_state["new_answer_value"] = ""

        # Add new Q&A
        st.markdown("## ➕ Add New Q&A")
        new_question = st.text_input("Enter a new question", key="new_question", value=st.session_state.get("new_question_value", ""))
        new_answer = st.text_area("Enter a new answer", key="new_answer", value=st.session_state.get("new_answer_value", ""))
        if st.button("Add"):
            if new_question and new_answer:
                new_row = pd.DataFrame({'質問': [new_question], '回答': [new_answer]})
                st.session_state['manual_data'] = pd.concat([st.session_state['manual_data'], new_row], ignore_index=True)
                st.session_state['manual_data'].to_csv('manual.csv', index=False, encoding='utf-8')
                st.success("The new Q&A has been added.")

                # Clear input fields
                clear_inputs()

                # Update the manual display
                # No need to rerun the app
            else:
                st.warning("Please enter both a question and an answer.")

        # Display the updated manual data
        st.markdown("## 📄 Current Manual")
        st.dataframe(st.session_state['manual_data'])

        # Display all questions and feedback
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
    else:
        st.error("Incorrect password.")
