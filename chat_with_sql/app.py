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


def get_sql_chain(db: SQLDatabase):
    prompt_template = ChatPromptTemplate.from_template(
        """ 
            You are an agent designed to interact with a SQL database.
            Given an input question, create a syntactically correct query to run, then look at the results of the query and return the answer.
            You can order the results by a relevant column to return the most interesting examples in the database.
            Take the below schema {schema} into consideration before executing the query to have understanding of the querying table.
            Never query for all the columns from a specific table, only ask for the relevant columns given the question.
            You have access to tools for interacting with the database.
            Only use the below tools. Only use the information returned by the below tools to construct your final answer.
            You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again 
            
            Provide only the SQL query without any additional explanation.
            If the query is complex don't use words like 'sql' or special keywords like '```'. Just return the query
         
            Please take the chat hisotry {chat_history} into consideration for having a previos chat context.

         
         Here are some examples:
         question: Give me all the employee details,
         query: SELECT emp_id, fname, lname, email, dept, salary, hire_date FROM employees;
         question: Give me only the fullnames of the employess having salary grater than 50000
         query: SELECT CONCAT_WS(' ', fname, lname) FROM employees WHERE salary > 50000;

         What's your question? {question}
        """
    )
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

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
                and so on. Tyr to make the response eye pleasing.

                Here are the details:\n
                User Question: {question}\n
                Database Scema: {schema}\n
                Sql query: {query}\n
                Sql query response: {query_response}\n
                Conversation_hisotry: {chat_history}
            """
    )

    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

    chain = (
        RunnablePassthrough.assign(query=sql_chain).assign(
            schema=lambda _: db.get_table_info(),
            query_response=lambda x: print(f"Executable query: {x['query']}")
            or db.run(x["query"]),
        )
        | prompt_template
        | model
        | StrOutputParser()
    )

    return chain.invoke({"question": user_question, "chat_history": chat_history})


if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(
            "Hi I am your sql assistant. You type your question in natural language and I will create the sql query"
        )
    ]

st.set_page_config(page_title="Chat with SQL database", page_icon="asd")

st.title("Chat with SQL Database")
st.session_state.disabled = True


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
