import sys
sys.path.insert(0, '.')

from core.rag.qa_system import qa

result = qa.answer_question("What are ESA rules?", [], None)
print("Answer:", result["answer"])
print("Sources:", result["sources"])