import json
import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.google_cloud_functions import SlackRequestHandler
import vertexai
from vertexai.generative_models import GenerativeModel, Tool
from vertexai.preview.generative_models import grounding


# 環境変数の読み込み
load_dotenv()

MAX_SUMMARIZED_LENGTH = 500
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_REACTION_KEY = os.environ["SLACK_REACTION_KEY"]
SLACK_PROCESSING_REACTION_KEY = os.environ["SLACK_PROCESSING_REACTION_KEY"]
PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")
MODEL_NAME = os.environ.get("GOOGLE_MODEL_NAME")

# Slackアプリの初期化
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    process_before_response=True,
)

# ヘルパー関数
def extract_urls(text):
    """テキストからURLを抽出する関数"""
    urls = re.findall(r"https?://[^\s<>]+", text)
    return urls


def debug_log(name, data):
    """デバッグ用のログを出力する関数"""
    if isinstance(data, dict):
        data = json.dumps(data, ensure_ascii=False)
    print(f"[DEBUG] {name} = {data}")


def extract_article_text(url):
    """指定したURLから記事の本文を抜き出す関数"""
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.string if soup.title else "タイトルが見つかりませんでした"

    debug_log("title", title)
    title = re.sub(r"<[^>]+>|[\n\r]+", " ", title)
    text = soup.find("body").get_text()
    text = re.sub(r"<[^>]+>", " ", text)
    info = f"Fallback to use 'requests'. text = {text}"

    return {"title": title, "text": text, "info": info}


def generate_summary(text):
    """記事テキストを要約する関数"""
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    model = GenerativeModel(
        MODEL_NAME,
        system_instruction="You are a helpful assistant that summarizes articles and extracts important keywords.",
        tools=[
            Tool.from_google_search_retrieval(
                google_search_retrieval=grounding.GoogleSearchRetrieval()
            ),
        ],
    )

    prompt=f'''以下の #文章 を #ルール に従い、日本語で要約してください。
またSNS発信のためハッシュタグをつけたいです。記事内容の特徴を表すキーワードを5つほど選んでください。
その際サービス名や製品名を優先するようにしてください。その後結果を JSON 形式で出力してください。最後に句読点はつけないでください。

#文章
{text}

#ルール
- 要約文は最大 {MAX_SUMMARIZED_LENGTH} 文字まで
- 製品名などの英語と日本語の文字列間は必ず半角スペースを入れてください
- 句読点の前後、括弧の前後、またYYYY年MM月DD日のような日付表現では、半角スペースは不要
- キーワードを上位3つまで入れてTwitter投稿用の文言も作る

#JSONフォーマット
{{"summary": "ここにサマリ文章", "keywords": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"], "tweet": "ここにTwitter投稿文言"}}'''

    response =  model.generate_content(
      [prompt],
      generation_config={
        "max_output_tokens": 8192,
        "temperature": 0.5,
        "top_p": 0.95,
      },
      stream=False,
    )

    json_text = response.text
    return json.loads(json_text)


def format_slack_post(title, url, text, date, keywords):
    """Slackに記事のサマリをブロック形式で投稿する関数"""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":point_right: *<{url}|{title}>* ({date})"
                    if date
                    else f":point_right: *<{url}|{title}>*"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"> {text}\n>`" + "` `".join(keywords) + "`",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": ":placard: _↑は生成AIによるまとめです。詳細は元記事を確認してください。_",
                }
            ],
        },
    ]
    return blocks


def process_url(text, say):
    """URLを処理する共通関数"""
    urls = extract_urls(text)
    url = urls[0] if urls else None
    if url is None:
        say("_⚠️ URL が見つかりませんでした。_")
        return

    response = requests.get(url, timeout=10)
    url = response.url
    debug_log("url (after requests.get())", url)

    article = extract_article_text(url)
    title = article["title"]
    text = article["text"]

    # 生成AIでサマリを作成
    generated = generate_summary(text)
    summary = generated["summary"]
    keywords = generated["keywords"]

    slack_response = format_slack_post(title, url, summary, None, keywords)
    say(
        blocks=slack_response,
        replace_original=True,
        response_type="in_channel",
        unfurl_links=False,
    )


def ignore_retry_request(request, ack, next):
    if "x-slack-retry-num" in request.headers:
        return ack()
    next()


app.use(ignore_retry_request)


# メッセージハンドラー
@app.message("https")
def handle_message(event, say):
    """メッセージを処理する関数"""
    text = event["text"]
    process_url(text, say)


# イベントハンドラー
@app.event("app_mention")
def handle_mention(event, say):
    """アプリがメンションされたときの処理"""
    text = event["text"]
    process_url(text, say)


@app.event("reaction_added")
def reaction_add(event, say, client):
    """リアクションが追加されたときの処理"""
    if event["reaction"] != SLACK_REACTION_KEY:
        return

    user = event["user"]
    channel = event["item"]["channel"]
    ts = event["item"]["ts"]

    # タイムスタンプでメッセージを特定
    conversations_history = client.conversations_history(
        channel=channel, oldest=ts, latest=ts, inclusive=1
    )

    messages = conversations_history.data["messages"]

    # メッセージが取得出来ない場合、スレッドからメッセージを特定
    if not messages:
        group_history = client.conversations_replies(channel=channel, ts=ts)
        messages = group_history.data["messages"]

    if messages and "attachments" in messages[0]:
        text = "{} {} {}".format(
            messages[0]["text"],
            messages[0]["attachments"][0]["title"],
            messages[0]["attachments"][0]["title_link"],
        )
    else:
        text = messages[0]["text"]
    text = re.sub(r"[|<>]", " ", text)
    debug_log("text", text)

    urls = extract_urls(text)
    url = urls[0] if urls else None
    if url is None:
        client.chat_postEphemeral(
            channel=channel, user=user, text="_⚠️URL is not found_"
        )
        return

    # 処理中リアクション追加
    client.reactions_add(channel=channel, timestamp=ts, name=SLACK_PROCESSING_REACTION_KEY)

    response = requests.get(url, timeout=10)
    url = response.url
    debug_log("url", url)

    # 記事タイトル、本文抜き出し
    article = extract_article_text(url)
    title = article["title"]
    text = article["text"]

    # 生成AIでサマリとキーワードを取得
    generated = generate_summary(text)
    summary = generated["summary"]
    keywords = generated["keywords"]

    # 処理中リアクション削除
    client.reactions_remove(channel=channel, timestamp=ts, name=SLACK_PROCESSING_REACTION_KEY)

    # スレッドへの返信として投稿
    slack_response = format_slack_post(title, url, summary, None, keywords)
    response = client.chat_postMessage(
        channel=channel,
        text=summary,
        blocks=slack_response,
        thread_ts=ts,
        unfurl_links=False,
    )
    return


# Google Cloud Functionsハンドラー
def slack_events_fn(request):
    """Google Cloud Functionsハンドラー"""
    slack_handler = SlackRequestHandler(app)
    return slack_handler.handle(request)
