from flask import Flask, render_template, jsonify, request, session
from src.helper import download_embeddings, get_session_history
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain.agents import initialize_agent, AgentType, Tool
from dotenv import load_dotenv
from src.prompt import *
import os
import uuid


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "my_super_secret_key_for_testing")  # <-- HERE


load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

embeddings = download_embeddings()

index_name = "medical-chatbot"
# Load the existing index

docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)

retriever = docsearch.as_retriever(search_type = "similarity", search_kwargs = {"k":3})

chat_model = ChatOpenAI(model = "gpt-4o")
prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessagePromptTemplate.from_template("{input}")
])

# Define the contextualize prompt properly
contextualize_q_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "Given a chat history and the latest user question, "
        "reformulate the question as a standalone question without answering it."
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessagePromptTemplate.from_template("{input}")
])

history_aware_retriever = create_history_aware_retriever(
    llm=chat_model,
    retriever=retriever,
    prompt = contextualize_q_prompt
)

question_answer_chain = create_stuff_documents_chain(chat_model,prompt)
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
store = {}
conversational_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer"
)
rag_tool = Tool(
    name="Medical_RAG",
    func=lambda query: conversational_rag_chain.invoke(
        {"input": query},
        config={"configurable": {"session_id": "agent_session"}}
    )["answer"],
    description="Answer medical questions using the knowledge base."
)
agent = initialize_agent(
    tools=[rag_tool],
    llm=chat_model,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False,
)

agent_with_history = RunnableWithMessageHistory(
    agent,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="output"
)
@app.route("/get", methods=["GET","POST"])
def chat():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]

    user_input = request.form["msg"].strip()
    print("User input:", user_input)

    # Handle greetings
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
    if user_input.lower() in greetings:
        return "Hello! I am your medical assistant. How can I help you today?"

    # Handle RAG queries
    try:
        response = agent_with_history.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}},
            handle_parsing_errors=True
        )
        # Extract only the final answer
        answer = response.get("output", "")
    
    except Exception as e:
        # Extract just the message about needing more context
        msg = str(e)
        if "The question is not specific enough" in msg:
            answer = "The question is not specific enough to determine what condition 'that' refers to. " \
                     "Please provide additional context so I can assist you effectively."
        else:
            answer = "⚠️ An error occurred. Please provide additional context or clarify the question."

    print("Agent answer:", answer)
    return str(answer)


@app.route("/")
def index():
    return render_template('chat.html')

if __name__=='__main__':
    app.run(host="0.0.0.0", port=8080, debug= True)