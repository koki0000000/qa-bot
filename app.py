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
page = st.sidebar.selectbox("Select your role", ["User", "Admin"])

if page == "User":
    # Streamlitアプリの設定
    st.title("Q&A Bot")
    st.write("This bot answers your questions based on our manual in any languages.")

    question = st.text_input("Enter your questions:")

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
                st.session_state['history'].append({'question': question, 'answer': ai_response})

                # フィードバックの収集
                feedback_options = ["Yes", "No"]
                feedback = st.radio(
                    "Was this answer usuful?", feedback_options, index=-1, key=f"feedback_{len(st.session_state['history'])}"
                )

                if feedback:
                    st.session_state['history'][-1]['feedback'] = feedback
                else:
                    st.session_state['history'][-1]['feedback'] = "未評価"

            except openai.error.OpenAIError as e:
                st.error(f"OpenAIへのリクエスト中にエラーが発生しました: {e}")
        else:
            st.warning("質問を入力してください。")

    # 質問履歴の表示
    st.markdown("## 質問履歴")
    for idx, qa in enumerate(st.session_state['history']):
        st.markdown(f"**質問 {idx+1}:** {qa['question']}")
        st.markdown(f"**回答 {idx+1}:** {qa['answer']}")
        st.markdown(f"**フィードバック {idx+1}:** {qa.get('feedback', '未評価')}")

    # フィードバック結果の保存
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
                    {'question': qa['question'], 'answer': qa['answer'], 'feedback': qa.get('feedback', '未評価')}
                )
                qa['feedback_saved'] = True  # 重複保存を防ぐ

        if new_data:
            feedback_data = pd.concat([feedback_data, pd.DataFrame(new_data)], ignore_index=True)
            feedback_data.to_csv('feedback.csv', index=False, encoding='utf-8')

    save_feedback(st.session_state['history'])

elif page == "Admin":
    # 管理者認証
    admin_password = st.sidebar.text_input("Enter your password", type="password")
    if admin_password == "koki":  # パスワードを設定
        st.success("Welcome to Admin Page")

        # マニュアルの表示
        st.markdown("## 現在のマニュアル")
        st.dataframe(manual_data)

        # 新しいQ&Aの追加
        st.markdown("## 新しいQ&Aを追加")
        new_question = st.text_input("新しい質問を入力してください")
        new_answer = st.text_area("新しい回答を入力してください")
        if st.button("追加"):
            if new_question and new_answer:
                new_row = pd.DataFrame({'質問': [new_question], '回答': [new_answer]})
                manual_data = pd.concat([manual_data, new_row], ignore_index=True)
                manual_data.to_csv('manual.csv', index=False, encoding='utf-8')
                st.success("新しいQ&Aが追加されました。")

                # 入力欄をクリア
                st.experimental_rerun()
            else:
                st.warning("質問と回答を入力してください。")

        # フィードバック結果の表示
        st.markdown("## フィードバック結果の集計")
        if os.path.exists('feedback.csv'):
            try:
                feedback_data = pd.read_csv('feedback.csv', encoding='utf-8')
                if not feedback_data.empty:
                    st.dataframe(feedback_data)
                    positive_feedback = feedback_data[feedback_data['feedback'] == 'はい'].shape[0]
                    negative_feedback = feedback_data[feedback_data['feedback'] == 'いいえ'].shape[0]
                    st.markdown(f"**役に立った:** {positive_feedback}件")
                    st.markdown(f"**役に立たなかった:** {negative_feedback}件")
                else:
                    st.warning("フィードバックデータがまだありません。")
            except pd.errors.EmptyDataError:
                st.warning("フィードバックデータがまだありません。")
        else:
            st.warning("フィードバックデータがまだありません。")
    else:
        st.error("パスワードが正しくありません。")
