import streamlit as st
import openai
import pandas as pd
import os

# OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load manual data
def load_manual():
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
            st.error(f"Error loading manual.csv: {e}")
            return pd.DataFrame(columns=['質問', '回答'])
    else:
        st.error("The manual.csv file was not found.")
        return pd.DataFrame(columns=['質問', '回答'])

manual_data = load_manual()

# Initialize session state for history
if 'history' not in st.session_state:
    st.session_state['history'] = []

# Page selection (User and Admin)
page = st.sidebar.selectbox("Select a page", ["User", "Admin"])

if page == "User":
    # Streamlit app configuration
    st.title("Q&A Bot")
    st.write("This bot answers your questions based on the manual. Please enter your question below.")

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
                st.success(f"Answer: {ai_response}")

                # Add question and answer to history
                st.session_state['history'].append({'question': question, 'answer': ai_response})

                # Collect feedback
                feedback_options = ["Yes", "No"]
                feedback = st.radio(
                    "Was this answer helpful?",
                    feedback_options,
                    index=None,
                    key=f"feedback_{len(st.session_state['history'])}"
                )

                if feedback:
                    st.session_state['history'][-1]['feedback'] = feedback
                else:
                    st.session_state['history'][-1]['feedback'] = "Not Rated"

            except openai.error.OpenAIError as e:
                st.error(f"An error occurred while contacting OpenAI: {e}")
        else:
            st.warning("Please enter a question.")

    # Display question history
    st.markdown("## Question History")
    for idx, qa in enumerate(st.session_state['history']):
        st.markdown(f"**Question {idx+1}:** {qa['question']}")
        st.markdown(f"**Answer {idx+1}:** {qa['answer']}")
        st.markdown(f"**Feedback {idx+1}:** {qa.get('feedback', 'Not Rated')}")

    # Save feedback results
    def save_feedback(history):
        if os.path.exists('feedback.csv'):
            try:
                feedback_data = pd.read_csv('feedback.csv', encoding='utf-8')
            except pd.errors.EmptyDataError:
                feedback_data = pd.DataFrame(columns=['question', 'answer', 'feedback'])
        else:
            feedback_data = pd.DataFrame(columns=['question', 'answer', 'feedback'])

        new_data = []
        for qa in history:
            if not qa.get('feedback_saved', False):
                new_data.append(
                    {'question': qa['question'], 'answer': qa['answer'], 'feedback': qa.get('feedback', 'Not Rated')}
                )
                qa['feedback_saved'] = True  # Prevent duplicate saves

        if new_data:
            feedback_data = pd.concat([feedback_data, pd.DataFrame(new_data)], ignore_index=True)
            feedback_data.to_csv('feedback.csv', index=False, encoding='utf-8')

    save_feedback(st.session_state['history'])

elif page == "Admin":
    # Admin authentication
    admin_password = st.sidebar.text_input("Enter the password", type="password")
    if admin_password == "koki":  # Set your password
        st.success("Accessed the admin page.")

        # Display the manual
        st.markdown("## Current Manual")
        st.dataframe(manual_data)

        # Add new Q&A
        st.markdown("## Add New Q&A")
        new_question = st.text_input("Enter a new question", key="new_question")
        new_answer = st.text_area("Enter a new answer", key="new_answer")
        if st.button("Add Q&A"):
            if new_question and new_answer:
                new_row = pd.DataFrame({'質問': [new_question], '回答': [new_answer]})
                manual_data = pd.concat([manual_data, new_row], ignore_index=True)
                manual_data.to_csv('manual.csv', index=False, encoding='utf-8')
                st.success("The new Q&A has been added.")

                # Clear input fields
                st.session_state["new_question"] = ""
                st.session_state["new_answer"] = ""
                # Rerun the app to update the manual display
                st.experimental_rerun()
            else:
                st.warning("Please enter both a question and an answer.")

        # Display feedback results
        st.markdown("## Feedback Summary")
        if os.path.exists('feedback.csv'):
            try:
                feedback_data = pd.read_csv('feedback.csv', encoding='utf-8')
                if not feedback_data.empty:
                    st.dataframe(feedback_data)
                    positive_feedback = feedback_data[feedback_data['feedback'] == 'Yes'].shape[0]
                    negative_feedback = feedback_data[feedback_data['feedback'] == 'No'].shape[0]
                    st.markdown(f"**Helpful:** {positive_feedback}")
                    st.markdown(f"**Not Helpful:** {negative_feedback}")
                else:
                    st.warning("There is no feedback data yet.")
            except pd.errors.EmptyDataError:
                st.warning("There is no feedback data yet.")
        else:
            st.warning("There is no feedback data yet.")
    else:
        st.error("Incorrect password.")
