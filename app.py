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

# 質問履歴をセッション状態で管理
if 'history' not in st.session_state:
    st.session_state['history'] = []

# ページ選択（ユーザー用と管理者用）
page = st.sidebar.selectbox("Select a page", ["User", "Admin"])

if page == "User":
    # Streamlitアプリの設定
    st.title("Q&A Bot")
    st.write("This bot answers your questions based on the manual. Please enter your question below.")

    question = st.text_input("Enter your question:")

    if st.button("Submit"):
        if question:
            # マニュアルの内容を結合してテキスト化
            manual_text = "\n".join(manual_data['質問'] + "\n" + manual_data['回答'])

            # OpenAIに質問とマニュアルを送信して回答を取得
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

                # 質問と回答を履歴に追加
                st.session_state['history'].append({'question': question, 'answer': ai_response, 'feedback': "Not Rated"})

            except openai.error.OpenAIError as e:
                st.error(f"An error occurred while contacting OpenAI: {e}")
        else:
            st.warning("Please enter a question.")

    # 質問履歴の表示とフィードバック収集
    st.markdown("## Question History")
    for idx, qa in enumerate(st.session_state['history']):
        st.markdown(f"**Question {idx+1}:** {qa['question']}")
        st.markdown(f"**Answer {idx+1}:** {qa['answer']}")

        if qa['feedback'] == "Not Rated":
            feedback_options = ["Please select", "Yes", "No"]
            feedback = st.selectbox(
                f"Was this answer helpful? (Question {idx+1})",
                feedback_options,
                key=f"feedback_{idx}"
            )
            if feedback != "Please select":
                qa['feedback'] = feedback
        else:
            st.markdown(f"**Feedback {idx+1}:** {qa['feedback']}")

    # フィードバック結果の保存
    def save_feedback():
        if os.path.exists('feedback.csv'):
            try:
                feedback_data = pd.read_csv('feedback.csv', encoding='utf-8')
            except pd.errors.EmptyDataError:
                feedback_data = pd.DataFrame(columns=['question', 'answer', 'feedback'])
        else:
            feedback_data = pd.DataFrame(columns=['question', 'answer', 'feedback'])

        new_data = []
        for qa in st.session_state['history']:
            if not qa.get('feedback_saved', False) and qa['feedback'] != "Not Rated":
                new_data.append({
                    'question': qa['question'],
                    'answer': qa['answer'],
                    'feedback': qa['feedback']
                })
                qa['feedback_saved'] = True  # 重複保存を防ぐ

        if new_data:
            feedback_data = pd.concat([feedback_data, pd.DataFrame(new_data)], ignore_index=True)
            feedback_data.to_csv('feedback.csv', index=False, encoding='utf-8')

    save_feedback()

elif page == "Admin":
    # 管理者認証
    admin_password = st.sidebar.text_input("Enter the password", type="password")
    if admin_password == "koki":  # パスワードを設定
        st.success("Accessed the admin page.")

        # マニュアルの表示
        st.markdown("## Current Manual")
        st.dataframe(manual_data)

        # 入力欄をクリアする関数を定義
        def clear_inputs():
            st.session_state["new_question"] = ""
            st.session_state["new_answer"] = ""

        # 新しいQ&Aの追加
        st.markdown("## Add New Q&A")
        new_question = st.text_input("Enter a new question", key="new_question")
        new_answer = st.text_area("Enter a new answer", key="new_answer")
        if st.button("Add Q&A"):
            if new_question and new_answer:
                new_row = pd.DataFrame({'質問': [new_question], '回答': [new_answer]})
                manual_data = pd.concat([manual_data, new_row], ignore_index=True)
                manual_data.to_csv('manual.csv', index=False, encoding='utf-8')
                st.success("The new Q&A has been added.")

                # 入力欄をクリア
                clear_inputs()

                # マニュアルの表示を更新
                st.experimental_rerun()
            else:
                st.warning("Please enter both a question and an answer.")

        # フィードバック結果の表示
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
