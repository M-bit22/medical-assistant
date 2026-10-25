import os
import streamlit as st
from dotenv import load_dotenv

from src.config import CHAT_MODELS, GENDERS, COMMON_SYMPTOMS, DURATIONS, LANGUAGES
from src.cache_manager import setup_cache
from src.chains import get_medical_chain, stream_narrative
from src.utils import parse_llm_json

load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="MediGuide AI - Symptom Assessment",
    page_icon="🩺",
    layout="wide"
)

# Mandatory Safety Banner on Top
st.error(
    "⚠️ **IMPORTANT MEDICAL & SAFETY NOTICE:** MediGuide AI is an educational AI prototype only. "
    "It is NOT a replacement for a licensed doctor, professional diagnosis, or emergency services. "
    "Never use this for actual medical treatment or life-threatening situations."
)

st.title("🩺 MediGuide AI")
st.caption("AI-Powered Medical Symptom Assessment and Patient Guidance Assistant")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Settings & Configuration")
    
    api_key_input = st.text_input(
        "Google API Key", 
        type="password", 
        value=os.getenv("GOOGLE_API_KEY", "")
    )
    
    model_name = st.selectbox("Select Chat Model", CHAT_MODELS)
    
    st.divider()
    st.subheader("🚀 Caching Configuration")
    cache_option = st.selectbox(
        "Select Cache Type",
        ["None", "In-Memory (RAM)", "SQLite (Disk)"]
    )
    setup_cache(cache_option)
    
    st.divider()
    st.markdown("### ℹ️ Disclaimer")
    st.info(
        "This tool provides preliminary educational guidance only. Always consult a "
        "qualified healthcare professional for medical concerns."
    )

if api_key_input:
    os.environ["GOOGLE_API_KEY"] = api_key_input

# Main Form Input
st.subheader("📋 Patient Information & Symptoms")

with st.form("symptom_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        age = st.text_input("Patient Age", placeholder="e.g., 30")
        gender = st.selectbox("Gender", GENDERS)
        selected_symptoms = st.multiselect("Select Symptoms", COMMON_SYMPTOMS)
        custom_symptoms = st.text_input("Additional Symptoms (Optional)", placeholder="e.g., mild shivering")
        duration = st.selectbox("Duration of Symptoms", DURATIONS)
        
    with col2:
        severity = st.slider("Symptom Severity (1 = Mild, 10 = Severe)", 1, 10, 3)
        existing_conditions = st.text_area("Existing Medical Conditions", placeholder="e.g., Asthma, Diabetes")
        current_medicines = st.text_area("Current Medications", placeholder="e.g., Inhaler as needed")
        notes = st.text_area("Additional Notes", placeholder="Any other relevant details...")
        language = st.selectbox("Answer Language", LANGUAGES)
        
    submitted = st.form_submit_button("🔍 Run Assessment")

if submitted:
    if not api_key_input:
        st.error("Please enter your Google API Key in the sidebar to proceed.")
        st.stop()
        
    if not selected_symptoms and not custom_symptoms:
        st.warning("⚠️ Please select or enter at least one symptom before submitting.")
        st.stop()
        
    # Combine selected and custom symptoms
    all_symptoms_list = selected_symptoms.copy()
    if custom_symptoms:
        all_symptoms_list.append(custom_symptoms)
    symptoms_str = ", ".join(all_symptoms_list)
    
    inputs = {
        "age": age if age else "Not specified",
        "gender": gender,
        "symptoms": symptoms_str,
        "duration": duration,
        "severity": str(severity),
        "existing_conditions": existing_conditions if existing_conditions else "None reported",
        "current_medications": current_medicines if current_medicines else "None reported",  # Fixed spelling here
        "notes": notes if notes else "None",
        "language": language
    }
    
    chain, llm = get_medical_chain(model_name)
    
    # Run Assessment and Display Results
    st.divider()
    st.subheader("📊 Assessment Results Dashboard")
    
    tabs = st.tabs(["📋 Structured Summary", "💬 Live Narrative Stream", "🔍 Retrieved Sources / Raw"])
    
    with tabs[0]:
        with st.spinner("Analyzing symptoms and generating guidance..."):
            try:
                raw_response = chain.invoke(inputs)
                parsed_data = parse_llm_json(raw_response)
                
                if "error" in parsed_data:
                    st.error(parsed_data["error"])
                    st.text(parsed_data.get("raw_output", ""))
                else:
                    urgency = parsed_data.get("urgency_level", "LOW").upper()
                    
                    # Urgency color-coded display
                    if urgency == "EMERGENCY":
                        st.error("🚨 **URGENCY LEVEL: EMERGENCY** - Seek immediate emergency medical help!")
                    elif urgency == "HIGH":
                        st.error("⚠️ **URGENCY LEVEL: HIGH** - Consult a healthcare professional promptly.")
                    elif urgency == "MEDIUM":
                        st.warning("⚡ **URGENCY LEVEL: MEDIUM** - Schedule an appointment with a doctor soon.")
                    else:
                        st.success("🟢 **URGENCY LEVEL: LOW** - Monitor symptoms at home and rest.")
                        
                    st.markdown("### 📌 Summary")
                    st.write(parsed_data.get("summary", "No summary provided."))
                    
                    st.markdown("### 🩺 Possible Conditions (For Education Only)")
                    conditions = parsed_data.get("possible_conditions", [])
                    if conditions:
                        for cond in conditions:
                            with st.expander(f"📌 {cond.get('name', 'Condition')}"):
                                st.write(cond.get('reason', ''))
                    else:
                        st.write("No specific conditions listed.")
                        
                    st.markdown("### 👣 Recommended Next Steps")
                    st.info(parsed_data.get("recommended_next_steps", ""))
                    
                    col_q, col_w = st.columns(2)
                    with col_q:
                        st.markdown("### ❓ Questions for Your Doctor")
                        for q in parsed_data.get("questions_for_doctor", []):
                            st.markdown(f"- {q}")
                            
                    with col_w:
                        st.markdown("### ⚠️ Warning Signs (Red Flags)")
                        for w in parsed_data.get("warning_signs", []):
                            st.markdown(f"- 🔴 {w}")
                            
            except Exception as e:
                st.error(f"An error occurred during execution: {e}")
                
    with tabs[1]:
        st.markdown("### ✍️ Live Streaming Guidance")
        try:
            st.write_stream(stream_narrative(llm, inputs))
        except Exception as e:
            st.error(f"Streaming failed: {e}")
            
    with tabs[2]:
        st.markdown("### 🔍 Raw Model Output Debugger")
        if 'raw_response' in locals():
            st.code(raw_response, language="json")
        else:
            st.info("Submit the form to view raw outputs.")