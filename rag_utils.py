from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.agents import initialize_agent, AgentType, Tool
from src.helper import download_embeddings
from src.prompt import system_prompt, contextualize_q_prompt
import os
from dotenv import load_dotenv
load_dotenv()

# ---------- ENV ----------
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

# ---------- RAG Setup ----------
embeddings = download_embeddings()
index_name = "medical-chatbot"
docsearch = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embeddings)
retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":3})
chat_model = ChatOpenAI(model="gpt-4o")

prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessagePromptTemplate.from_template("{input}")
])

contextualize_q_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(contextualize_q_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessagePromptTemplate.from_template("{input}")
])

history_aware_retriever = create_history_aware_retriever(
    llm=chat_model,
    retriever=retriever,
    prompt=contextualize_q_prompt
)

question_answer_chain = create_stuff_documents_chain(chat_model, prompt)
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

conversational_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    lambda session_id: ChatMessageHistory(),
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer"
)

rag_tool = Tool(
    name="Medical_RAG",
    func=lambda query, session_id=None: conversational_rag_chain.invoke(
        {"input": query},
        config={"configurable": {"session_id": session_id}}
    )["answer"],
    description="Answer medical questions using the knowledge base."
)

agent = initialize_agent(
    tools=[rag_tool],
    llm=chat_model,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False
)

agent_with_history = RunnableWithMessageHistory(
    agent,
    lambda session_id: ChatMessageHistory(),
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="output"
)
