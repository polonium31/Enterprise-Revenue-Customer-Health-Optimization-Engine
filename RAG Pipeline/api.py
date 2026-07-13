import os
import json
import snowflake.connector
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Allow your React frontend to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to your React app's local URL (e.g., http://localhost:3000) for security later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the expected format of incoming requests
class ChatRequest(BaseModel):
    message: str

# --- Keep your existing Snowflake execution function exactly as it was ---
def execute_snowflake_query(sql_query: str) -> str:
    forbidden_keywords = ["drop", "delete", "truncate", "update", "insert", "alter"]
    if any(keyword in sql_query.lower() for keyword in forbidden_keywords):
        return "Error: Security policy violation. Destructive actions are prohibited."

    sanitized_query = sql_query.strip().rstrip(';')
    if "limit" not in sanitized_query.lower():
        sanitized_query += " LIMIT 50"

    conn = None
    try:
        conn = snowflake.connector.connect(
            user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            database="ECOMMERCE",
            schema="ECOMMERCE_DN_SCHEMA",
            role="ECOMMERCE_AI_ROLE",     
            warehouse="AI_QUERY_WH" 
        )
        cursor = conn.cursor()
        cursor.execute(sanitized_query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        result_data = [dict(zip(columns, row)) for row in rows]
        return json.dumps(result_data)
    except Exception as e:
        return f"Database Execution Failure: {str(e)}"
    finally:
        if conn:
            conn.close()

# --- Initialize Azure Clients Once at Startup ---
project_client = AIProjectClient(
    endpoint=os.environ.get("FOUNDRY_PROJECT_ENDPOINT"),
    credential=DefaultAzureCredential(),
)
openai_client = project_client.get_openai_client()
AGENT_NAME = "ecommerce-analyst-model-gpt"

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    """The API endpoint that your frontend will call."""
    
    try:
        # 1. Send the user's message to the Azure AI Agent
        response = openai_client.responses.create(
            input=request.message,
            extra_body={"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}},
        )

        input_list: list[ResponseInputParam] = []

        # 2. Check for Snowflake Function Calls
        for item in response.output:
            if getattr(item, "type", None) == "function_call":
                if item.name == "execute_snowflake_query":
                    sql_args = json.loads(item.arguments)
                    
                    # Execute locally against Snowflake
                    sql_result = execute_snowflake_query(**sql_args)
                    
                    # Format the result to return to the model
                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=json.dumps({"result": sql_result}),
                        )
                    )

        # 3. If a query was run, send the data back to AI for interpretation
        if input_list:
            response = openai_client.responses.create(
                input=input_list,
                previous_response_id=response.id,
                extra_body={"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}},
            )

        # Parse the JSON string from the AI into a Python dictionary before sending to the frontend
        return json.loads(response.output_text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))