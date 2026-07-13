import streamlit as st
import requests
import json
import pandas as pd

# Set up the page
st.set_page_config(page_title="Ecommerce AI Analyst", page_icon="📊")
st.title("Ecommerce Data Analyst")
st.caption("Ask questions about your Snowflake database in plain English.")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Listen for user input
if prompt := st.chat_input("E.g., What were our top 3 products by revenue in Jan 2026?"):
    
    # 1. Display user message in UI
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 2. Add user message to session history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 3. Call your FastAPI backend
    with st.chat_message("assistant"):
        with st.spinner("Querying Snowflake..."):
            try:
                # Send the POST request to your local FastAPI server
                response = requests.post(
                    "http://localhost:8000/chat",
                    json={"message": prompt}
                )
                response.raise_for_status()
                
                # Parse the response from the API
                data = response.json()
                
                # Safe parsing block (in case the AI returns plain text instead of JSON)
                if isinstance(data, str):
                    try:
                        clean_data = data.replace("```json", "").replace("```", "").strip()
                        data = json.loads(clean_data)
                    except json.JSONDecodeError:
                        data = {"summary": data, "sql_query_used": "No query generated.", "data": "[]"}
                
                summary = data.get("summary", "No summary provided.")
                sql_query = data.get("sql_query_used", "")
                raw_data = data.get("data", "[]")
                
                # 1. Display the AI's plain English summary
                st.markdown(summary)
                
                # 2. Convert raw JSON data into a clean, user-friendly table
                try:
                    # Parse the stringified JSON from Snowflake
                    parsed_raw_data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                    
                    if parsed_raw_data:
                        df = pd.DataFrame(parsed_raw_data)
                        
                        # Format any column with 'REVENUE', 'PRICE', or 'COST' in the name as currency
                        for col in df.columns:
                            if any(keyword in col.upper() for keyword in ['REVENUE', 'PRICE', 'COST', 'SUBTOTAL']):
                                df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else x)
                        
                        # Display the interactive table directly in the chat!
                        st.dataframe(df, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.warning("Could not format the raw data into a table.")

                # 3. Keep the SQL query hidden in a collapsible expander for transparency
                with st.expander("View Database Query"):
                    st.code(sql_query, language="sql")
                
                # Save the AI response to chat history
                st.session_state.messages.append({"role": "assistant", "content": summary})
                
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend. Is your FastAPI server running on port 8000?")
            except Exception as e:
                st.error(f"An error occurred: {e}")