import os
import streamlit as st
from pydantic import BaseModel, ValidationError
from PyPDF2 import PdfReader
from docx import Document

# ✅ Import the Samaira OpenAI client
from openai import OpenAI

# -------------------------------------------
# ✅ Samaira OpenAI client setup
# -------------------------------------------
client = OpenAI(
    api_key="b79f26cc155d387cdcf0dc98ea4c89ecb31484ead5ee426b826654d79b9537f2",  
    base_url="https://inference.samaira.ai/openai/v1"
)

# -------------------------------------------
# ✅ Pydantic schema for input validation
# -------------------------------------------
class SummarizerPrompt(BaseModel):
    text: str

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

    # ✅ Make sure response is dict-like: print debug if needed
    print("RAW Response:", response)
    print("TYPE:", type(response))

    # ✅ Correct: Samaira's client returns a dict-like object
    if hasattr(response, "choices"):
        return response.choices[0].message.content
    elif isinstance(response, dict):
        return response["choices"][0]["message"]["content"]
    else:
        return str(response)

# -------------------------------------------
# ✅ File extractor
# -------------------------------------------
def extract_file_text(uploaded_file):
    if uploaded_file.name.endswith(".txt"):
        try:
            return uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            return uploaded_file.read().decode("latin-1")
    elif uploaded_file.name.endswith(".pdf"):
        pdf = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif uploaded_file.name.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return ""

# -------------------------------------------
# ✅ Streamlit UI
# -------------------------------------------
st.title("📄✨ Pydantic-AI Summarizer")
st.write("Paste text or upload a file (.txt, .pdf, .docx)")

text_input = st.text_area("✏️ Paste text here:", height=200)
uploaded_file = st.file_uploader("📂 Upload a file", type=["txt", "pdf", "docx"])

file_text = extract_file_text(uploaded_file) if uploaded_file else ""
final_input = file_text or text_input

if st.button("✨ Summarize"):
    if final_input.strip() == "":
        st.warning("Please add text or upload a file.")
    else:
        try:
            user_prompt = SummarizerPrompt(text=final_input)
            with st.spinner("Summarizing..."):
                result = summarize_text(user_prompt)
                st.subheader("✅ Summary")
                st.write(result)
        except ValidationError as ve:
            st.error(f"Input validation failed: {ve}")
