import os
import json
import snowflake.connector
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam

# Load environment variables from .env file
load_dotenv()

def execute_snowflake_query(sql_query: str) -> str:
    """Executes a read-only SQL query against the Ecommerce star schema and returns the data."""
    # Strict security checks to block destructive operations
    forbidden_keywords = ["drop", "delete", "truncate", "update", "insert", "alter"]
    if any(keyword in sql_query.lower() for keyword in forbidden_keywords):
        return "Error: Security policy violation. Destructive actions are prohibited."

    # Append a protective row limit if the model forgot to add one
    sanitized_query = sql_query.strip().rstrip(';')
    if "limit" not in sanitized_query.lower():
        sanitized_query += " LIMIT 50"

    conn = None
    try:
        # Establish connection using securely mapped environment variables
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

        # Fetch data and map to a readable array of dictionaries for the LLM
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        result_data = [dict(zip(columns, row)) for row in rows]

        return json.dumps(result_data)

    except Exception as e:
        return f"Database Execution Failure: {str(e)}"
    finally:
        if conn:
            conn.close()

def main():
    # Initialize the project client using Entra ID authentication
    project_client = AIProjectClient(
        endpoint=os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "https://ecommerce-ai-model.services.ai.azure.com/api/projects/proj-default"),
        credential=DefaultAzureCredential(),
    )

    system_instructions = """You are an expert enterprise data analyst specializing in Snowflake SQL for an e-commerce platform. Your primary responsibility is to analyze natural language questions from business users, translate them into valid Snowflake SQL queries, and interpret the data accurately.

    Database Schema Context:
    You have access to the following tables in the ECOMMERCE database and ECOMMERCE_DN_SCHEMA schema:
    1. CUSTOMERS (customer_key, first_name, middle_name, last_name, customer_segment, lifetime_value...)
    2. PRODUCTS (product_key, sku, product_name, category, cost_price, retail_price...)
    3. Date_Table (date_key, full_date, month_name, year, quarter...)
    4. SALES_INVOICES (fact_sales_key, order_date_key, payment_status, line_item_subtotal...)

    Strict Query Formulation Rules:
    - Revenue / Sales Calculation: When asked about "sales" or "revenue", always calculate this using SUM(line_item_subtotal) from the SALES_INVOICES table.
    - Date Filtering (CRITICAL): When users ask about dates (e.g., "March 2026"), always JOIN Sales_Invoices.order_date_key to Date_Table.date_key. 
    - THE MONTH RULE: The Date_Table.month_name column EXCLUSIVELY uses 3-letter abbreviations. You will fail the request if you use full month names. You MUST map 'January' -> 'Jan', 'February' -> 'Feb', 'March' -> 'Mar', etc., in your WHERE clause.
    - Product Aggregations: When users ask for "top products", join SALES_INVOICES to Products using product_key, group by product_name, sum the subtotal, order descending, and apply the requested LIMIT.
    - Safety: Only generate read-only SELECT queries.
    
    Output Formatting:
    You MUST return your final response to the user as a valid, stringified JSON object. Do not include markdown blocks. Use the exact schema below:
    {
      "sql_query_used": "The exact SQL query you generated and ran",
      "summary": "A clean, natural language summary answering the user's original question",
      "data": "The raw data values returned from the database"
    }
    """

    # 1. Define the tool explicitly using JSON Schema
    snowflake_tool = FunctionTool(
        name="execute_snowflake_query",
        parameters={
            "type": "object",
            "properties": {
                "sql_query": {
                    "type": "string",
                    "description": "The read-only Snowflake SQL query to execute based on the user's question.",
                },
            },
            "required": ["sql_query"],
            "additionalProperties": False,
        },
        description="Executes a read-only SQL query against the Ecommerce star schema and returns the data.",
        strict=True,
    )

    openai_client = project_client.get_openai_client()

    print("Binding tools to agent...")
    agent = project_client.agents.create_version(
        agent_name="ecommerce-analyst-model-gpt",
        definition=PromptAgentDefinition(
            model=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5.4"),
            instructions=system_instructions,
            tools=[snowflake_tool],
        ),
    )

    print("Agent configured and ready. Requesting query generation...")

    # 2. Make the initial request
    response = openai_client.responses.create(
        input="What were our top 3 products by revenue in Jan 2026?",
        extra_body={"agent_reference": {"name": agent.name, "version": agent.version, "type": "agent_reference"}},
    )

    input_list: list[ResponseInputParam] = []

    # 3. Intercept the function call from the model
    for item in response.output:
        if getattr(item, "type", None) == "function_call":
            if item.name == "execute_snowflake_query":
                sql_args = json.loads(item.arguments)
                print(f"\n[AI is running query] -> {sql_args['sql_query']}")
                
                # Execute locally against Snowflake
                sql_result = execute_snowflake_query(**sql_args)
                
                # 4. Format the result to return to the model
                input_list.append(
                    FunctionCallOutput(
                        type="function_call_output",
                        call_id=item.call_id,
                        output=json.dumps({"result": sql_result}),
                    )
                )

    # 5. Push the Snowflake data back to the Agent for the final JSON summary
    if input_list:
        print("\n[Query successful] -> Sending data back to AI for interpretation...")
        response = openai_client.responses.create(
            input=input_list,
            previous_response_id=response.id,
             extra_body={"agent_reference": {"name": agent.name, "version": agent.version, "type": "agent_reference"}},
        )

    print(f"\nFinal AI Output:\n{response.output_text}")

if __name__ == "__main__":
    main()