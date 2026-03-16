import streamlit as st
import google.generativeai as genai
import json
import os
from PyPDF2 import PdfReader
from dotenv import load_dotenv

# Load local environment variables from .env
load_dotenv()

# Set the API key directly from the environment variable
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith('.pdf'):
        reader = PdfReader(uploaded_file)
        return " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif uploaded_file.name.endswith('.txt'):
        return uploaded_file.getvalue().decode("utf-8")
    return ""

def evaluate_document(policy, document):
    if not api_key:
        raise ValueError("API Key is missing. Please set GEMINI_API_KEY in your .env file or deployment secrets.")
    
    # 1. Dynamically find an allowed model for your specific API key
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # Look for a flash model first, then a pro model, or just take whatever is allowed
    target_model = None
    for m in available_models:
        if 'gemini-1.5-flash' in m:
            target_model = m
            break
    if not target_model:
        for m in available_models:
            if 'flash' in m or 'pro' in m:
                target_model = m
                break
    if not target_model and available_models:
        target_model = available_models[0]
        
    if not target_model:
        raise ValueError("Your API key does not have access to any text generation models.")
        
    # 2. Initialize the dynamically found model
    model = genai.GenerativeModel(target_model) 
    
    prompt = f"""
    You are an expert compliance AI agent who proces the document text abd make strucutured decisions. Evaluate the DOCUMENT against the POLICY.
    
    POLICY:
    {policy}
    
    DOCUMENT:
    {document}
    
    RULES:
    1. If the document fully complies with the policy, decision is PASS.
    2. If the document violates the policy, decision is FAIL.
    3. CRITICAL: If the document is missing necessary information, decision MUST be NEEDS_INFO.
    
    You MUST return ONLY a raw JSON object with this exact structure. Do not include markdown formatting or backticks:
    {{
        "decision": "PASS", 
        "confidence": 95,
        "reasons": ["reason 1", "reason 2"],
        "evidence": ["quote 1", "quote 2"],
        "explanation": "Short summary"
    }}
    """
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.1
        )
    )
    
    try:
        raw_text = (response.text or "").strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        data = json.loads(raw_text.strip())
        if not isinstance(data, dict):
            raise ValueError("Model output was not a JSON object.")

        # Decision validation / normalization
        decision_raw = str(data.get("decision", "")).upper()
        if decision_raw not in {"PASS", "FAIL", "NEEDS_INFO"}:
            decision_raw = "NEEDS_INFO"
        data["decision"] = decision_raw

        # Confidence normalization to integer 0–100
        conf = data.get("confidence", 0)
        try:
            conf_int = int(conf)
        except (TypeError, ValueError):
            conf_int = 0
        conf_int = max(0, min(100, conf_int))
        data["confidence"] = conf_int

        # Ensure list types for reasons/evidence
        for key in ("reasons", "evidence"):
            val = data.get(key, [])
            if isinstance(val, str):
                val = [val]
            elif not isinstance(val, list):
                val = []
            data[key] = val

        if "explanation" not in data or not isinstance(data["explanation"], str):
            data["explanation"] = ""

        return data

    except Exception:
        raise ValueError(f"Failed to parse JSON. Raw AI output was: '{response.text}'")


# --- Streamlit UI ---
st.set_page_config(page_title="AI-Pass Document Evaluator", page_icon="📄", layout="wide")

st.title("📄 AI-Pass Document Decision Agent")
st.markdown("Evaluate documents against policies with autonomous reasoning and structured outputs.")

# Warning if API key is not found
if not api_key:
    st.error("⚠️ GEMINI_API_KEY not found in environment variables. The app will not work until this is configured.")

# Main layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Define Policy / Rules")
    policy_text = st.text_area("Enter the policy rules the document must follow:", height=200, 
                               placeholder="e.g., Invoices must include a Date, a Vendor Name, and a Total Amount greater than $0.")

with col2:
    st.subheader("2. Input Document")
    input_method = st.radio("Document Input Method", ["Upload File (PDF/TXT)", "Paste Text"], horizontal=True)
    
    document_text = ""
    if input_method == "Upload File (PDF/TXT)":
        uploaded_file = st.file_uploader("Upload an invoice or document", type=["pdf", "txt"])
        if uploaded_file:
            document_text = extract_text_from_file(uploaded_file)
            st.success("File processed successfully!")
    else:
        document_text = st.text_area("Paste document text here:", height=150)

# Execution
st.markdown("---")
if st.button("Analyze Document", type="primary", use_container_width=True):
    if not policy_text.strip():
        st.error("⚠️ Please provide a policy to evaluate against.")
    elif not document_text.strip():
        st.error("⚠️ Please provide a document to evaluate.")
    else:
        with st.spinner("Analyzing the document..."):
            try:
                result = evaluate_document(policy_text, document_text)
                
                # Display Results
                st.subheader("📊 Evaluation Result")
                
                decision = result.get("decision", "ERROR")
                color = "green" if decision == "PASS" else "red" if decision == "FAIL" else "orange"
                st.markdown(f"### Decision: <span style='color:{color}'>{decision}</span>", unsafe_allow_html=True)
                
                st.metric("AI Confidence Score", f"{result.get('confidence', 0)}%")
                st.markdown(f"**Explanation:** {result.get('explanation', '')}")
                
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.markdown("**Reasons:**")
                    for reason in result.get("reasons", []):
                        st.markdown(f"- {reason}")
                with col_res2:
                    st.markdown("**Evidence Found:**")
                    for ev in result.get("evidence", []):
                        st.markdown(f"- _{ev}_")
                        
                with st.expander("View Raw JSON Output"):
                    st.json(result)
                
                # Convert the Python dictionary to a formatted JSON string
                # Convert the Python dictionary to a formatted JSON string
                # Convert the Python dictionary to a formatted JSON string
                json_string = json.dumps(result, indent=4)
                
                st.download_button(
                    label="📥 Export Result as JSON",
                    data=json_string,
                    file_name="evaluation_result.json",
                    mime="application/json",
                    use_container_width=True
                )
                # -------------------------------------

                    
            except Exception as e:
                st.error(f"An error occurred during evaluation: {e}")
