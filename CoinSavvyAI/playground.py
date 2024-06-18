from langchain_community.utilities.serpapi import SerpAPIWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import PyPDF2
from flask import Flask, request, jsonify
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.faiss import FAISS
from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
from langchain.agents import Tool, OpenAIMultiFunctionsAgent, OpenAIFunctionsAgent, AgentExecutor
from langchain.prompts import MessagesPlaceholder, PromptTemplate
from langchain.memory import ConversationBufferMemory
import os
from langchain.schema import SystemMessage

app = Flask(__name__)

# This it the language model we'll use. We'll talk about what we're doing below in the next section
openai_api_key = "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"
os.environ['SERPAPI_API_KEY'] = "06066c87d3fa649ee744e8e7984f5d8f38616b313c3e1d25b616ddef05d3c8e5"
LLM_ChatModel = ChatOpenAI(temperature=.4, openai_api_key=openai_api_key)
# LLM_model_2 = ChatOpenAI(temperature=.6, )

# TextSplitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=20
)

# Embeddings
embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)


# Load and extract data from pdf
def extract_text_from_pdf(file_paths):
    # Initialize an empty string to store the text
    text = ""

    # Iterate through each file path
    for file_path in file_paths:
        # Open the PDF file in read-binary mode
        with open(file_path, 'rb') as pdf_file:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            # Get the number of pages in the PDF
            num_pages = len(pdf_reader.pages)

            # Loop through each page and extract text
            for index in range(num_pages):
                page = pdf_reader.pages[index]
                text += page.extract_text()

    return text


file_paths = ['Personal Finance for Dummies.pdf']  # Add more file paths as needed
my_text = extract_text_from_pdf(file_paths)

# Break down data into chunks
docs = text_splitter.create_documents([my_text])

for i, text in enumerate(docs):
    text.metadata["source"] = f"{i}-pl"

# We need to add now some type of cache, so we can use the embeddings without embed the documents again if already

# Set the storage
storage = LocalFileStore("./cache/")
# Set the cached embedder
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    embeddings, storage, namespace=embeddings.model
)

# Embed documents and store it in a vectorDatabase
db = FAISS.from_documents(docs, cached_embedder)
retriever = db.as_retriever()  # Our Database as a Retriever

"""
We have our Retriever Storage, now we want the LLM to do some kind of things: 

-Summarize Topics in a concise and understandable way
-Maintain a friendly conversation
-Reply to questions over the topics using documents and known knowledge

Means we need to set a Tool for each of these functionalities.
"""

SystemMsg = SystemMessage(
    content="""
            Your name is 'CoinSavvy AI' and you can only offer information on topics about finance. You are clueless
            in any other domain or any other unrelated topic. Use all the relevant tools necessary. Prioritize user
            friendliness and suggest follow questions and conversations based on the previous interaction between you
            and the user. Note that you have only have knowledge in topics in finance. Use knowledge provided by the tools
            but you may add supporting explanations from your own knowledge.
            Include EMOJIS within the finance context as well when you're providing information
            in your responses to make the interaction more lively and friendly.
            
            Make sure to always display your final answer as output to the user after using any of the tools provided.
            The response must include the appropriate finance emojis.
            """
)

# Tool for Answering questions based on document
prompt_template = """
Instruction: Your name is CoinSavvy AI, and you are highly knowledgeable in finance renowned for your expertise in topics of finance.
            Provide comprehensive and accurate responses to queries related to various topic areas, including  personal finance, covering investments, loans and debt, interest, banking fees, identity theft, risk management, and financial planning.
            Draw upon your deep understanding of financial principles, disciplines, and relevant topics to offer well-reasoned and informed responses.
            Prioritize clarity, precision, and friendliness in your responses, ensuring that the information provided is up-to-date.
            You only know about financial related topics. 
            Make sure to always display your final answer as output to the user. 
            Answer to the question at the end based on this context :
Context: {context}
Question: {question}
"""
prompt1 = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)
chain_type_kwargs = {"prompt": prompt1}
qa = RetrievalQA.from_chain_type(llm=LLM_ChatModel, chain_type="stuff", retriever=retriever,
                                 chain_type_kwargs=chain_type_kwargs)

# Document Summarizer Tool
prompt_template_2 = """
Instruction: You are supposed to use this context {context} to produce a Summary worthy of a finance topic.
Question: {question}
"""
prompt2 = PromptTemplate(
    template=prompt_template_2, input_variables=["context", "question"]
)

chain_type_kwargs = {"prompt": prompt2}
qa_summary = RetrievalQA.from_chain_type(llm=LLM_ChatModel, chain_type="stuff", retriever=retriever,
                                         chain_type_kwargs=chain_type_kwargs)

# qa_search = APIChain.api_answer_chain(llm=LLM_ChatModel, chain_type="stuff", chain_type_kwargs=chain_type_kwargs, agent="zero-shot-react-description")
# APIChain.api_answer_chain
# tool_names = ["serpapi"]
# qa.search = load_tools(tool_names)


serpapi = SerpAPIWrapper()

# Initializing tools
tools = ([
    # retrieve_docs,
    Tool(
        name="finance_expert",
        func=qa.run,
        description="Useful when asked about questions related to finance"
    ),
    Tool(
        name="finance_summarizer",
        func=qa_summary.run,
        description="Useful to summarize documents related to Financial Topics"
    ),
    Tool(
        name="finance_search",
        func=serpapi.run,
        description="Useful when providing real time information related to finance"
    )

])

"""
Agents Initializer and Execution
"""

# We Create the Prompt using the (MultiFunction Agent) and add a place to store the History of our chat
MEMORY_KEY = "chat_history"  # Memorykey

prompt = OpenAIMultiFunctionsAgent.create_prompt(
    system_message=SystemMsg,
    extra_prompt_messages=[MessagesPlaceholder(variable_name=MEMORY_KEY)]
)

# The Buffer Memory that will hold the Chat History
memory = ConversationBufferMemory(memory_key=MEMORY_KEY, return_messages=True)

# Initialize the Agent with the prompt , the tools and the Type (here: MultiFUNCTION AGENT)
agent = OpenAIFunctionsAgent(llm=LLM_ChatModel, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True, return_intermediate_steps=False)

# Main Part of the code
print("Hello Welcome to CoinSavvy AI, how can I help you today? (Note to exit, type 'exit')\n ")


# while True:
#     query = input("User: ")
#     if query.lower() == 'exit':
#         break
#     else:
#         # Execute the QA chain
#         response = agent_executor({"input": query})
#         print(f"CoinSavvy AI:{response['output']}")

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    query = data['query']

    # Execute the QA chain
    response = agent_executor({"input": query})

    return jsonify({"response": response['output']})


if __name__ == '__main__':
    app.run(debug=True)
# #
# def query(text):
#     messages = [
#         HumanMessage(content=text),
#         SystemMessage(content=SystemMsg)
#     ]
#     print("CoinSavvy AI: ", LLM_ChatModel.invoke(messages))
#
#
# def main():
#     text = input("Type your prompt: ")
#     while "quit" not in text:
#         query(text)
#         if "quit" not in text:
#             text = input("\nType your prompt (type quit to exit): ")
#         else:
#             query(text)
#
#
# if __name__ == "__main__":
#     main()
