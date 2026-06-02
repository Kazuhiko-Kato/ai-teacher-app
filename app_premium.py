import streamlit as st
import os
import base64
import csv  # ✨ ログ保存用に追加
from datetime import datetime  # ✨ 日時取得用に追加
from google import genai

# ==========================================
# 📄 ページ基本設定（ワイドモード）
# ==========================================
st.set_page_config(
    page_title="中学生AI先生 〜プレミアム学習環境〜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ここから修正：プルダウンの文字色を黒にする最強コード ---
st.markdown("""
<style>
/* ① 閉じている時の箱の中の文字（選択済みの文字）を黒にする */
div[data-baseweb="select"] span,
div[data-baseweb="select"] div {
    color: #000000 !important;
}

/* ② クリックして開いた後のリストの文字を黒にする */
div[data-baseweb="popover"] ul li,
div[data-baseweb="popover"] ul li span,
div[data-baseweb="popover"] ul li div,
ul[data-baseweb="menu"] li span,
ul[data-baseweb="menu"] li {
    color: #000000 !important;
}
</style>
""", unsafe_allow_html=True)
# --- ここまで修正 ---
# ==========================================
# 🔑 金庫（secrets）からAPIキーと合言葉を安全に読み込む
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    SECRET_PASSWORD = st.secrets["APP_PASSWORD"]  # ✨ コードに直接書かず、金庫から呼び出す！
except (FileNotFoundError, KeyError):
    st.error("⚠️ APIキーまたはパスワードが見つかりません。`.streamlit/secrets.toml` を設定してください。")
    st.stop()

# ==========================================
# 🔒 簡易アクセス制限システム（ログイン画面）
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; color: #ffffff; margin-top: 50px;'>🔒 会員限定：中学生AI先生</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #e0e0e0;'>このアプリを利用するには、教室から案内された「合言葉」を入力してね。</p>", unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([1, 1.5, 1])
    with center_col:
        user_password = st.text_input("合言葉を入力してください", type="password", label_visibility="collapsed")
        if st.button("🔑 ロックを解除する", use_container_width=True):
            if user_password == SECRET_PASSWORD:  # 金庫から出したパスワードと照合
                st.session_state.logged_in = True
                st.success("認証に成功したよ！先生の部屋へ移動します...")
                st.rerun()
            else:
                st.error("❌ 合言葉が違っているみたい。もう一度確認してみてね！")
                
    st.stop()


# ==========================================
# 🔄 セッション状態（記憶の部屋）の初期化
# ==========================================
if "started" not in st.session_state:
    st.session_state.started = False
if "under_construction" not in st.session_state:  # ✨ これを追加！
    st.session_state.under_construction = False
if "construction_message" not in st.session_state: # ✨ これを追加！
    st.session_state.construction_message = ""
if "current_subject" not in st.session_state:  # ✨ これを追加！
    st.session_state.current_subject = "数学"
if "current_unit" not in st.session_state:
    st.session_state.current_unit = "未選択"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "message": "まだ質問はありません。下の入力欄から先生に話しかけてみよう！"}
    ]
if "grading_result" not in st.session_state:
    st.session_state.grading_result = None


# ==========================================
# 📊 ログ自動保存システム
# ==========================================
def save_log(action, grade, unit, content):
    """学習ログをCSVファイルに自動保存する関数"""
    log_file = "learning_logs.csv"
    
    # 現在の時刻を「年-月-日 時:分:秒」の形式で取得
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ファイルが存在しない場合は、最初だけヘッダー（列名）を書く
    file_exists = os.path.exists(log_file)
    
    try:
        with open(log_file, mode="a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["日時", "アクション", "学年", "単元", "内容"])
            
            # データを1行追記
            writer.writerow([now, action, grade, unit, content])
    except Exception as e:
        print(f"ログ保存エラー: {e}")  # 画面には出さず、裏側でエラーを記録



# ==========================================
# 🚧 未実装機能（工事中）の自動ガードシステム
# ==========================================
def check_under_construction(grade, term, subject, unit):
    # 🟢 PoC用に「中学1年生」の「1学期」なら全教科（数学・英語・国語）動くように設定
    is_ready = (grade == "中学1年生" and term == "1学期")
    
    if not is_ready:
        # ✨ ここではメッセージを画面に出さず、記憶するだけにします
        st.session_state.under_construction = True
        st.session_state.construction_message = f"選んでくれた「{grade}」の「{subject} - {unit}」は、現在AI先生が次のアップデートに向けて一生懸命準備中だよ！\n\n今回の体験版では、**【中学1年生の1学期】**の学習ができるから、左のメニューから選び直してスタートしてみてね！"
        
        save_log("工事中遭遇", grade, unit, f"未実装エリアへのアクセス（{term}/{subject}）")
        st.rerun() # リロードして中央画面にバトンタッチ！
    else:
        # 💡 準備OKなエリアが選ばれたら、フラグを折ってそのまま下へスルーさせるだけ！
        st.session_state.under_construction = False


# ==========================================
# 👈 左側サイドバー（メニュー設定欄）
# ==========================================
with st.sidebar:
    st.title("👨‍🏫 中学生AI先生")
    st.caption("~プレミアム学習環境~")
    st.write("---")
    
    selected_grade = st.selectbox("学年を選んでね", ["中学1年生", "中学2年生", "中学3年生"])
    selected_term = st.selectbox("学期を選んでね", ["1学期", "2学期", "3学期"])
    selected_subject = st.selectbox("教科を選んでね", ["数学", "英語", "国語"]) # ✨ 新規追加
    
    st.write("**今日の学習内容**")
    
    # ✨ 選んだ教科によって単元のリストを切り替える
    if selected_subject == "数学":
        unit_list = ["正の数と負の数", "文字式の計算", "一元一次方程式", "比例と反比例", "データの分布"]
    elif selected_subject == "英語":
        unit_list = ["アルファベットと発音", "be動詞と一般動詞", "代名詞"]
    elif selected_subject == "国語":
        unit_list = ["小説・物語文", "説明文・論理的文章", "言葉の単位・文法"]
        

    selected_unit = st.radio("選択してください", unit_list, label_visibility="collapsed")
    st.write("---")
    
    # =========================================================
    # ✨【リアルタイムチェック】メニューが切り替わった瞬間に作動
    # =========================================================
    is_ready = (selected_grade == "中学1年生" and selected_term == "1学期")
    if is_ready:
        # 1年生の1学期が選ばれたら、ボタンを押す前でも自動で工事中ロックを解除する
        st.session_state.under_construction = False
    
    # =========================================================
    # 👉 学習スタートボタン
    # =========================================================
    if st.button("👉 この単元の学習をスタート", type="primary"):
        # 1. まず工事中かどうかをチェック（1年1学期以外なら、ここでTrueになってリロードされる）
        check_under_construction(selected_grade, selected_term, selected_subject, selected_unit)
        
        # 2. 通常通りの学習スタート処理
        st.session_state.started = True
        st.session_state.current_subject = selected_subject
        st.session_state.current_unit = selected_unit       
        st.session_state.grading_result = None
        
        save_log("授業開始", selected_grade, f"{selected_subject}-{selected_unit}", "新しい単元のロード")
        
        if "content_text" in st.session_state:
            del st.session_state.content_text
        st.rerun()


# ==========================================
# 🖼️ バックグラウンド画像の読み込みとCSS
# ==========================================
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

image_filename = "picture.png"
if os.path.exists(image_filename):
    bin_str = get_base64_of_bin_file(image_filename)
    background_css = f"""
    <style>
    /* アプリ背景設定 */
    [data-testid="stAppViewContainer"] {{
        background-image: linear-gradient(rgba(14, 17, 23, 0.88), rgba(14, 17, 23, 0.88)), url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    [data-testid="stSidebar"] {{
        background-color: #11151c;
    }}
    
    /* 基本の文字色は強制白一色化 */
    h1, h2, h3, h4, h5, h6, p, span, label, li, ul, ol, div, small {{
        color: #ffffff !important;
    }}
    
    /* ✨ここが今回の最強の修正！ 白設定の直後に「でもプルダウンは黒！」と宣言する */
    div[data-testid="stSelectbox"] * {{
        color: #000000 !important;
    }}
    div[data-baseweb="popover"] *, ul[data-baseweb="menu"] * {{
        color: #000000 !important;
    }}
    
    /* ボタン内の文字色を非ホバー時でもはっきり white に表示 */
    .stButton > button {{
        color: #ffffff !important;
        background-color: #262730;
        border: 1px solid #464855;
    }}
    /* プライマリボタン（スタートボタン）の目立たせ設定 */
    .stButton > button[data-testid="baseButton-primary"] {{
        background-color: #ff4b4b;
        border: none;
    }}
    </style>
    """
    st.markdown(background_css, unsafe_allow_html=True)
# ==========================================
# 🏛️ 中央・右側のメイン画面レイアウト
# ==========================================
# ✨ ここに工事中メッセージを中央最優先で出す仕掛けを挟みます！
if st.session_state.under_construction:
    st.info(f"🚧 **AI先生からのお知らせ** 🚧\n\n{st.session_state.construction_message}")
    st.stop() # 💡 ここで止めることで、中央にメッセージを出しつつ、下の古い画面を描画させません

col1, col2 = st.columns([1.2, 1.0])

# --- 1️⃣ 左メインエリア：学習コンテンツ表示エリア ---
with col1:
    st.markdown(f"<h2 style='color: #ffffff;'>📖 現在の学習内容：{st.session_state.current_unit}</h2>", unsafe_allow_html=True)
    st.write("")
    
    if not st.session_state.started:
        st.markdown(
            """
            <div style='color: #ffffff; font-size: 18px; line-height: 1.6; font-weight: bold;'>
                <span style='color: #ffeb3b;'>👈 左のメニュー</span> から学習したい学年と学習内容を選んで、<br>
                <span style='color: #ffeb3b;'>スタートボタン</span> を押してください！
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        if "content_text" not in st.session_state:
            if not GEMINI_API_KEY:
                st.error("⚠️ APIキーが正しく読み込めていません。")

            else:
                try:
                    with st.spinner("先生が今日の黒板（授業内容）を準備しています..."):
                        client = genai.Client(api_key=GEMINI_API_KEY)
                        
                        # 🔴【プロンプトを修正】特定の単元の具体例を削除し、どんな単元にも対応できるように変更
                        
                        
                        prompt = f"""
                        あなたは、不登校の小中学生を専門に学習支援を行っている、非常に優しく共感力の高いプロの{st.session_state.current_subject}教師です。
                        生徒が自宅で一人でも安心してワクワクしながら学べるよう、中学1年生の{st.session_state.current_subject}の単元「{st.session_state.current_unit}」について、以下の構成でオリジナル教材を作成してください。

                        【1. 今日のポイント（解説）】
                        ・最初に「今日この単元を選んで勉強を始めようとした行動」そのものを、優しく褒めて認めてあげてください。
                        ・「{st.session_state.current_unit}」の核心となる重要な概念について、直感的に理解できるよう、身近な例え話を必ず交えて解説してください。
                        ・専門用語を並べるのではなく、中学生に語りかけるような優しい口調（「〜だよ」「〜してみよう！」）を徹底してください。
                        ・一画面で読みやすいよう、適度な改行と箇条書き、Markdownでの太字（**強調**）を使って、視覚的にスッキリ整理してください。

                        【2. 確認テストに挑戦！】
                        ・上記の解説内容が理解できたかを「スモールステップ」で確かめるための、記述式の問題を【1問だけ】作成してください。
                        ⚠️【超重要・絶対厳守】
                        ここには「問題の答え」や「正解の解説」を絶対に書かないでください。問題文が終わる箇所で文章を完全に終了させてください。
                        """

                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt
                        )
                        st.session_state.content_text = response.text
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ 授業の生成中にエラーが起きました: {str(e)}")

        if "content_text" in st.session_state:
            st.markdown(
                f"""
                <div style='background-color: rgba(255,255,255,0.05); padding: 20px; border-radius: 8px; margin-bottom: 20px; line-height: 1.6;'>
                    {st.session_state.content_text}
                </div>
                """, unsafe_allow_html=True
            )
            
            st.markdown("<h4 style='color: #ffffff;'>キミの答えを入力してね：</h4>", unsafe_allow_html=True)
            student_answer = st.text_input("答えを入力", key="student_answer_input", label_visibility="collapsed")
            
            if st.button("提出する", type="secondary"):
                if student_answer and GEMINI_API_KEY:
                    try:
                        with st.spinner("先生が丸付けをしています..."):
                            client = genai.Client(api_key=GEMINI_API_KEY)
                            
                            grading_prompt = f"""
                            
                            あなたは中学校の【{st.session_state.current_subject}教師】です。
                           あなたが出題した問題に対して、生徒が答えを提出しました。

                            
                            【あなたが出題した問題内容】
                            {st.session_state.content_text}
                            
                            【生徒が提出した解答】
                            {student_answer}
                            
                            ⚠️【超重要・採点ステップ】
                            ステップ1：生徒の解答は一度完全に無視して、出題した問題文を自分でよく読み、「真の正解」を論理的に逆算・思考してください。
                            ステップ2：あなたが計算した「真の正解」と、生徒の解答（{student_answer}）を厳しく見比べてください。生徒の答えに引きずられてはいけません。
                            ステップ3：【判定】を決定してください。完全一致、または意味が全く同じなら「正解」、違っていれば「不正解」です。
                            
                            【出力フォーマット】
                            必ず以下の形式に則って、中学生向けに優しく出力してください。
                            
                            【採点結果】
                            （ここに「正解！おめでとう！」または「残念！おしい！」と書いてください）
                            
                            【先生からの解説】
                            （なぜその答えになるのか、計算のプロセスや考え方をステップバイステップで教えてあげてください。不正解の場合は、答えを直接教えずに、どこが間違っているかのヒントを出して、もう一度考え直すように促してください。）
                            """
                            grading_response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=grading_prompt
                            )
                            st.session_state.grading_result = grading_response.text
                            # 👇ここに以下の1行を追加！
                            save_log("テスト提出", "中学1年生", st.session_state.current_unit, f"生徒の解答: {student_answer} / 採点結果: {grading_response.text[:100]}...")

                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ 採点中にエラーが起きました: {str(e)}")
            
            if st.session_state.grading_result:
                st.write("---")
                st.markdown(
                    f"""
                    <div style='background-color: rgba(76, 175, 80, 0.15); padding: 20px; border-radius: 8px; border: 1px solid #4caf50;'>
                        <h3 style='color: #4caf50; margin-top: 0px;'>📢 先生からの採点結果</h3>
                        <div style='color: #ffffff; line-height: 1.6; white-space: pre-wrap;'>
                            {st.session_state.grading_result}
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )

# --- 2️⃣ 右メインエリア：質問チャットエリア ---
with col2:
    st.markdown("<h3 style='color: #ffffff; margin-bottom: 0px;'>💬 質問はこちらから</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #e0e0e0; font-size: 14px; margin-bottom: 15px;'>授業中でもテスト中でも、いつでも質問してね。</p>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <style>
        .chat-container {
            background-color: rgba(0, 0, 0, 0.6); 
            border: 1px solid #444; 
            border-radius: 5px; 
            padding: 15px; 
            margin-bottom: 15px;
            height: 380px;
            overflow-y: auto;
        }
        .user-text { color: #8ed2e6; font-size: 16px; margin-bottom: 12px; line-height: 1.5; }
        .ai-text { color: #ffffff; font-size: 16px; margin-bottom: 12px; line-height: 1.5; }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    chat_html = "<div class='chat-container'>"
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            chat_html += f"<div class='user-text'><b>🙋‍♂️ キミ:</b> {chat['message']}</div>"
        else:
            chat_html += f"<div class='ai-text'><b>👨‍🏫 先生:</b> {chat['message']}</div>"
    chat_html += "</div>"
    st.markdown(chat_html, unsafe_allow_html=True)
    
    st.markdown("<p style='color: #ffffff; font-size: 14px; margin-bottom: 5px;'>わからないことがあれば、いつでも聞いてね！</p>", unsafe_allow_html=True)
    
    # AIへの問い合わせロジック
    def ask_gemini_teacher(user_input):
        try:
            with st.spinner("先生がわかりやすい解説を考えています..."):
                client = genai.Client(api_key=GEMINI_API_KEY)
               
                # 🔴 不登校の生徒に寄り添う「伴走型」のチャット指示書（完全回答バージョン）
                chat_prompt = f"""
                あなたは、不登校の小中学生を専門に教えている、非常に優しく共感力の高いプロの{st.session_state.current_subject}教師です。
                生徒から「{user_input}」という質問やメッセージが届きました。
                以下の【指導方針】を絶対に守って、生徒に返事（チャット）をしてください。

                【指導方針】
                1. 最初の1行目で、質問してくれた勇気や行動を「素晴らしいね！」「聞いてくれて嬉しいよ」と必ず褒めてください。
                2. 生徒の質問に対して、ヒントで終わらせず、最後まで分かりやすく「完全な答えと解説」を直接教えてあげてください。
                3. どうしてその答えになるのか、理由や手順をステップバイステップで優しく丁寧に説明してください。
                4. 生徒が「わからない」「むずかしい」と弱音を吐いたときは、勉強の話を一度置いて、「難しく感じるのは当然だよ」「焦らなくて大丈夫」と心に寄り添う言葉をかけてください。
                5. 文章は一度にたくさん送らず、中学生がチャットでパッと読めるように、短く簡潔に、改行を使って記述してください。
                """
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=chat_prompt
                )

                st.session_state.chat_history.append({"role": "assistant", "message": response.text})
        except Exception as e:
            st.session_state.chat_history.append({"role": "assistant", "message": f"❌ 通信エラー: {str(e)}"})

    # 入力フォーム構造
    with st.form(key="chat_form", clear_on_submit=True):
        user_query = st.text_input("質問を入力してね", label_visibility="collapsed")
        submit_button = st.form_submit_button(label="💬 質問を送る", use_container_width=True)
        
        
        if submit_button and user_query:
            st.session_state.chat_history.append({"role": "user", "message": user_query})
            if not GEMINI_API_KEY:
                st.session_state.chat_history.append({"role": "assistant", "message": "⚠️ APIキーが設定されていません。"})

            else:
                ask_gemini_teacher(user_query)
            # 👇ここに以下の1行を追加！
                save_log("質問送信", "中学1年生", st.session_state.current_unit, f"質問内容: {user_query}")

            st.rerun()



