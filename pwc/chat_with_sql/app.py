from dotenv import load_dotenv
import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import URL
from model import Pulse_PC_Ace, Sku_Brand_Mapping, Sales_Data, Targets_Data, Stockiest_HQ_Mapping_Ace, get_schema_info

RED = '\033[91m'
END = '\033[0m'
GREEN = '\033[92m'

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

load_dotenv()

def connect_db(host, port, username, password, database):
    db_url = URL.create(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
        drivername="postgresql",
    )
    return SQLDatabase.from_uri(db_url)

# db = connect_db("localhost", 5432, "postgres", "Password@123", "Stockiest_HQ")
# db._sample_rows_in_table_info = 0

classes = [Pulse_PC_Ace, Sku_Brand_Mapping, Stockiest_HQ_Mapping_Ace, Sales_Data, Targets_Data]
schema_info = get_schema_info(classes)

def get_sql_chain():
    db_prompt_template = ChatPromptTemplate([
        SystemMessage("You are an AI assistant who can understand human intent and convert it to an postgres sql query."),
        ("human",
        """
            Table schema long with column name, data type and description of the column
            {schema}
            Please take the chat hisotry {chat_history} into consideration for having a previos chat context.

            Tips:
                - Total sales value or target value should be multiple of amount of sales or target and units

            Guidelines:
                - Query only relevant columns based on the question.
                - Use the exact column names provided.
                - Consider the data type of column provided in schema
                - Caste column values to other data type if required
                - Provide only the SQL query without any additional explanation or characters like 'sql' or backticks.

            User question: {question}
        """)
    ])
    sql_chain = (
    RunnablePassthrough.assign(schema=lambda _: schema_info)
    | db_prompt_template
    | llm
    | StrOutputParser()
)
    return sql_chain

def get_response_chain(db:SQLDatabase):
    sql_chain = get_sql_chain()

    response_prompt_template = ChatPromptTemplate.from_template(
        """
            Based upon the user's question, database schema, sql query, and sql query response after execution, 
            you will return a response in human understandable english language along with sql query.

            Guideline
                - If the response has multiple values, restructure it in tabular format
                - If the response has single value, add proper prefic and suffix phrases to understand what the value means w.r.t to the user question.
                -  make the response eye pleasing.

            Here are the details:\n
            User Question: {question}\n
            Database Scema: {schema}\n
            Sql query: {query}\n
            Sql query response: {query_response}\n
            Conversation_hisotry: {chat_history}
        """
    )

    response_chain = (
        RunnablePassthrough.assign(query=sql_chain).assign(
            schema=lambda _: schema_info, query_response=lambda x: db.run(x["query"].replace("sql","").replace("```", ""))
        )
        | response_prompt_template
        | llm
        | StrOutputParser()
    )
    return response_chain


st.set_page_config(page_title="Chat with SQL database", page_icon="asd")

st.title("Chat with SQL Database")
if 'disabled' not in st.session_state:
    st.session_state.disabled = True
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(
            "Hi I am your sql assistant. You type your question in natural language and I will create the sql query"
        )
    ]

with st.sidebar:
    st.subheader("Settings")
    st.write("Connect to the database to start chatting")
    st.text_input(label="host", value="localhost", key="host")
    st.text_input(label="port", value="5432", key="port")
    st.text_input(label="username", value="postgres", key="username")
    st.text_input(
        label="password", type="password", value="Password@123", key="password"
    )
    st.text_input(label="database", value="bank_db", key="database")

    if st.button("Connect"):
        st.session_state.db = connect_db(
            host=st.session_state["host"],
            port=st.session_state["port"],
            username=st.session_state["username"],
            password=st.session_state["password"],
            database=st.session_state["database"],
        )
        st.success("Connected to database")
        st.session_state.disabled = False

for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("HUMAN"):
            st.markdown(message.content)

user_question = st.chat_input(placeholder="Type here...", key="question", disabled=st.session_state.disabled)

# while True:
#     question = input(f"{RED}You: ")
#     if question.lower() == 'quit':
#         break
#     chat_history.append(HumanMessage(question))
#     response = response_chain.invoke({'question': question, 'chat_history': chat_history})
#     chat_history.append(AIMessage(response))
#     print(f"{GREEN}AI: {response}")

if user_question is not None and user_question.strip() != "":
    st.session_state.chat_history.append(HumanMessage(user_question))
    with st.chat_message("HUMAN"):
        st.markdown(user_question)
    chain = get_response_chain(st.session_state.db)
    response = chain.invoke({"question": user_question, "chat_history": st.session_state.chat_history}) 
    st.session_state.chat_history.append(AIMessage(response))
    with st.chat_message("AI"):
        st.markdown(response)