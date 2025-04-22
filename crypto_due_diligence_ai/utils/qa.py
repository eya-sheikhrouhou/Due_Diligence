from langchain.llms import Ollama
from langchain.chains.question_answering import load_qa_chain

def ask_question(question, docs):
    llm = Ollama(model="mistral")
    chain = load_qa_chain(llm, chain_type="stuff")
    answer = chain.run(input_documents=docs, question=question)

    red_flag_keywords = [
        "scam", "illegal", "risk", "unregistered", "unlicensed",
        "ponzi", "rug pull", "lawsuit", "cease and desist", "breach"
    ]
    red_flag = any(keyword in answer.lower() for keyword in red_flag_keywords)
    return answer, red_flag

def improve_answer(question, current_answer):
    llm = Ollama(model="mistral")
    prompt = f"Improve the following answer to make it more clear, concise, and insightful for the question: {question}\n\nAnswer: {current_answer}"
    improved = llm(prompt)
    return improved