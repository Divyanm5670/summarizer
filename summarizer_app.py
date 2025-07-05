import os
import streamlit as st
from pydantic import BaseModel, HttpUrl, ValidationError
from PyPDF2 import PdfReader
from docx import Document
from newspaper import Article
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()


api_key = os.getenv("API_KEY")
# -------------------------------------------
# ✅ Samaira OpenAI client setup
# -------------------------------------------
client = OpenAI(
    api_key=api_key,
    base_url="https://inference.samaira.ai/openai/v1"
)

# -------------------------------------------
# ✅ Pydantic schemas for input validation
# -------------------------------------------
class SummarizerPrompt(BaseModel):
    text: str

class URLInput(BaseModel):
    url: HttpUrl

# -------------------------------------------
# ✅ Function to call Samaira.ai LLM
# -------------------------------------------
def summarize_text(validated_prompt: SummarizerPrompt):
    response = client.chat.completions.create(
        model="mistral-7b-instruct-v0.3",
        stream=False,
        messages=[
            {"role": "system", "content": "You are a helpful summarizer."},
            {"role": "user", "content": f"Summarize this in bullet points:\n\n{validated_prompt.text}"}
        ]
    )
    return response.choices[0].message.content

# -------------------------------------------
# ✅ Extract text from file
# -------------------------------------------
def extract_file_text(uploaded_file):
    if uploaded_file.name.endswith(".txt"):
        try:
            return uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            return uploaded_file.read().decode("latin-1")
    elif uploaded_file.name.endswith(".pdf"):
        pdf = PdfReader(uploaded_file)
        return "\n".join(
            page.extract_text() for page in pdf.pages if page.extract_text()
        )
    elif uploaded_file.name.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return ""

# -------------------------------------------
# ✅ Extract text from URL using newspaper3k
# -------------------------------------------
def extract_text_from_url(url: str) -> str:
    article = Article(url)
    try:
        article.download()
        article.parse()
        text = article.text.strip()
        if not text:
            return "[Extractor: No text found. Try downloading and uploading the PDF instead.]"
        return text
    except Exception as e:
        print(f"Failed to scrape URL: {e}")
        return "[Extractor: Failed to scrape. Try downloading and uploading the PDF instead.]"

# -------------------------------------------
# ✅ Extract transcript from YouTube
# -------------------------------------------
def extract_text_from_youtube(url: str) -> str:
    try:
        video_id = None
        if "youtube.com/watch?v=" in url:
            video_id = url.split("v=")[-1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("/")[-1].split("?")[0]
        if not video_id:
            return "[Extractor: Invalid YouTube URL format.]"

        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        text = " ".join([entry['text'] for entry in transcript_list]).strip()
        if not text:
            return "[Extractor: Transcript not found or empty.]"
        return text

    except TranscriptsDisabled:
        return "[Extractor: Captions are disabled for this video.]"
    except NoTranscriptFound:
        return "[Extractor: No transcript available for this video.]"
    except Exception as e:
        print(f"Failed to get YouTube transcript: {e}")
        return "[Extractor: Failed to get transcript.]"

# -------------------------------------------
# ✅ Streamlit UI
# -------------------------------------------
st.title("📄✨ Pydantic-AI Summarizer")

# 👉 Select input type in sidebar
with st.sidebar:
    st.header("⚙️ Input Options")
    input_choice = st.radio(
        "Choose your input source:",
        ("Paste Text", "Upload File", "Webpage URL", "YouTube URL")
    )

text_input, file_text, url_text, youtube_text = "", "", "", ""

if input_choice == "Paste Text":
    text_input = st.text_area("✏️ Paste your text here:", height=200)

elif input_choice == "Upload File":
    uploaded_file = st.file_uploader("📂 Upload a file (.txt, .pdf, .docx)", type=["txt", "pdf", "docx"])
    if uploaded_file:
        file_text = extract_file_text(uploaded_file)

elif input_choice == "Webpage URL":
    url_input = st.text_input("🌐 Enter webpage URL:")
    if url_input:
        try:
            valid_url = URLInput(url=url_input)
            with st.spinner("Scraping webpage..."):
                url_text = extract_text_from_url(str(valid_url.url))
        except ValidationError:
            st.warning("Invalid webpage URL format.")
        if url_text.startswith("[Extractor"):
            st.warning(url_text)  # Show warning only

elif input_choice == "YouTube URL":
    youtube_input = st.text_input("📹 Enter YouTube video URL:")
    if youtube_input:
        try:
            valid_youtube = URLInput(url=youtube_input)
            with st.spinner("Fetching YouTube transcript..."):
                youtube_text = extract_text_from_youtube(str(valid_youtube.url))
        except ValidationError:
            st.warning("Invalid YouTube URL format.")
        if youtube_text.startswith("[Extractor"):
            st.warning(youtube_text)  # Show warning only

# ✅ Use only valid extractions for final input
clean_url_text = url_text if url_text and not url_text.startswith("[Extractor") else ""
clean_youtube_text = youtube_text if youtube_text and not youtube_text.startswith("[Extractor") else ""

final_input = (
    file_text
    or clean_url_text
    or clean_youtube_text
    or text_input
)

# 👉 Summarize button
if st.button("✨ Summarize"):
    if not final_input.strip():
        st.warning("Please provide some input!")
    else:
        try:
            user_prompt = SummarizerPrompt(text=final_input)
            with st.spinner("Generating summary..."):
                summary = summarize_text(user_prompt)
                st.subheader("✅ Summary")
                st.write(summary)
        except ValidationError as ve:
            st.error(f"Input validation failed: {ve}")
