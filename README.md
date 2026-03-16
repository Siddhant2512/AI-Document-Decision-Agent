# AI-Pass Document Decision Agent

A 24-hour technical evaluation for the AI-Pass Orchestration Platform. This application allows users to upload documents, define a policy, and use an AI agent to determine if the document complies, outputting a structured, explainable decision.

## Live Demo
[Insert your live Streamlit link here after deployment]

## Architecture & Tech Stack
* **Frontend/Backend:** Single-page app built with [Streamlit](https://streamlit.io/) so non-technical users can interact with the agent easily.
* **LLM Engine:** Gemini via `google-generativeai`. The app dynamically picks an allowed text model for the provided API key (preferring `gemini-1.5-flash` when available).
* **Data Handling:** `PyPDF2` for document text extraction and direct JSON parsing/validation of the model output.

## How the Reasoning Works
The system uses **prompt-enforced structured JSON output**:

1. The user provides:
   - Policy/rules text
   - Document text (uploaded PDF/TXT or pasted text)
2. The app constructs a single prompt that:
   - Injects the policy and document
   - Defines rules for when to return `PASS`, `FAIL`, or `NEEDS_INFO`
   - Specifies the exact JSON structure to return (`decision`, `confidence`, `reasons`, `evidence`, `explanation`)
3. Gemini returns a JSON-looking string, which the app:
   - Strips any accidental markdown fences
   - Parses with `json.loads`
   - **Validates/normalizes**:
     - Forces `decision` into `PASS` / `FAIL` / `NEEDS_INFO` (anything else becomes `NEEDS_INFO`)
     - Clamps `confidence` to an integer 0–100
     - Ensures `reasons` and `evidence` are lists of strings
     - Ensures `explanation` is always a string

This gives you a predictable, structured result without relying on server-side JSON schema enforcement.

**Handling Missing Information (Reliability):**
The prompt strictly instructs the agent to return `NEEDS_INFO` if the document lacks the necessary context to make a definitive PASS/FAIL judgment. The low temperature (`0.1`) minimizes hallucination.

## Limitations & Simplifications
* **Context Window:** Currently limited to the standard token limits of the Gemini Flash context window. Very large PDFs would require chunking and a vector database (RAG).
* **Parsing:** Simple text extraction via PyPDF2 drops complex layout contexts (like complex tables in invoices). In a real production environment, I would use an OCR + Layout aware parser (e.g., Docling or AWS Textract).

## What I Would Improve Next (Bonus)
1. **Multi-Agent Workflow:** Split the task into an "Extractor Agent" (pulling structured facts from the doc) and an "Evaluator Agent" (comparing facts to rules) to increase accuracy.
2. **Conversation History:** Add a session state to allow the user to chat with the document and ask *why* it failed in a conversational interface.
3. **Enterprise Auth & Logging:** Track evaluations in a Postgres database to monitor the LLM's pass/fail distribution over time.

## Current Bonus Feature Implemented
* **Export result as JSON:** After each run, the structured evaluation is shown and can also be downloaded as a `evaluation_result.json` file via a Streamlit download button. This makes it easy to integrate the output into other systems or share it with reviewers.
