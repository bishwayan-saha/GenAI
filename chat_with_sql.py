from dotenv import load_dotenv
import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import URL

load_dotenv()


def connect_db(host, username, password, database):
    db_url = URL.create(
        host=host,
        username=username,
        password=password,
        database=database,
        drivername="postgresql",
    )
    return SQLDatabase.from_uri(db_url)


def get_sql_chain(db: SQLDatabase):
    prompt_template = ChatPromptTemplate.from_template(
        """ 
            You are an intelligent agent designed to interact with a **Postgres** SQL database. Your task is to generate accurate and syntactically correct SQL queries based on the user's input question.

            ### Responsibilities:
            - Analyze the user's question and generate a suitable SQL query.
            - Refer to the provided schema `{schema}` to understand the structure of the database.
            - Consider the chat history `{chat_history}` for context from prior messages.
            - Use only the tools provided to you to interact with the database.
            - Construct your final answer solely based on the results returned by these tools.

            ### Guidelines:
            - **Do not query all columns** (`SELECT *`). Only include the columns relevant to the user's question.
            - You may order the results by a meaningful column to return the most relevant or interesting data.
            - Always **double-check** your query before executing it.
            - If a query fails, **revise and retry** with a corrected version.
            - If SQL inbuilt funtions need to be used, remember, that should be compatible with postgres

            ### Output Rules:
            - Return **only the SQL query** with no explanation or formatting.
            - **Do not use words like "SQL" or code formatting** (e.g., `sql`, triple backticks) even for complex queries.

            ---

            **I want to know** `{question}`

        """
    )
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    return (
        RunnablePassthrough.assign(schema=lambda _: db.get_table_info())
        | prompt_template
        | model
        | StrOutputParser()
    )


def get_final_response(user_question: str, db: SQLDatabase, chat_history: list):
    sql_chain = get_sql_chain(db)
    prompt_template = ChatPromptTemplate.from_template(
            """
                You are an AI assistant who understands user's questions.
                Based upon the user's question, database schema, sql query, and sql query response after execution, 
                you will return a response in human understandable english language.

                If the response has multiple values, try to restructure in tabular format
                If the response has single value, add proper answer to understand what the value means w.r.t to the user question
                and so on. Try to make the response formatted.

                Here are the details:\n
                User Question: {question}\n
                Database Scema: {schema}\n
                Sql query: {query}\n
                Sql query response: {query_response}\n
                Conversation_hisotry: {chat_history}
            """
    )

    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    chain = (
        RunnablePassthrough.assign(query=sql_chain).assign(
            schema=lambda _: db.get_table_info(),
            query_response=lambda x: print(f"Executable query: {x['query']}")
            or db.run(x["query"].replace("```sql", "").replace("```", "")),
        )
        | prompt_template
        | model
        | StrOutputParser()
    )

    return chain.invoke({"question": user_question, "chat_history": chat_history})


if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(
            "Hi I am an intelligent assist. You type your question and I will try to answer using my tools"
        )
    ]

st.set_page_config(page_title="Chat with SQL database", page_icon="asd")

st.title("Chat with SQL Database")
st.session_state.disabled = True if not st.session_state.get("db") else False


with st.sidebar:
    st.subheader("Settings")
    st.write("Connect to the database to start chatting")
    st.text_input(label="host", value="ep-cool-leaf-a1sn945g-pooler.ap-southeast-1.aws.neon.tech", key="host")
    st.text_input(label="username", value="neondb_owner", key="username")
    st.text_input(
        label="password", type="password", value="npg_oYRTCrUmf75l", key="password"
    )
    st.text_input(label="database", value="neondb", key="database")

    if st.button("Connect"):
        st.session_state.db = connect_db(
            host=st.session_state["host"],
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

user_question = st.chat_input(
    placeholder="Type your message ...",
    key="question",
    disabled=st.session_state.disabled,
)

if user_question is not None and user_question.strip() != "":
    st.session_state.chat_history.append(HumanMessage(user_question))
    with st.chat_message("HUMAN"):
        st.markdown(user_question)
    with st.chat_message("AI"):
        response = get_final_response(
            user_question, st.session_state.db, st.session_state.chat_history
        )
        # sql_chain = get_sql_chain(st.session_state.db)
        # response = sql_chain.invoke({'question': user_question, 'chat_history': st.session_state.chat_history})
        st.markdown(response)
    st.session_state.chat_history.append(AIMessage(response))


