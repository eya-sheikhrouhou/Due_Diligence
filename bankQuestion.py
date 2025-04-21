import pymongo
from datetime import datetime

# Connexion à MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")  # Remplacer par l'URL de ta MongoDB si nécessaire
db = client["due_diligence"]  # Crée une base de données appelée "due_diligence"
questions_collection = db["questions"]  # Crée une collection appelée "questions"

# Exemple de banque de questions pour différentes catégories
questions_data = [
    # Legal
    {"question_text": "Is the project compliant with current international regulations?", "category": "Legal", "created_at": datetime.now()},
    {"question_text": "Has the project been involved in any legal disputes?", "category": "Legal", "created_at": datetime.now()},
    {"question_text": "Does the project adhere to intellectual property rights?", "category": "Legal", "created_at": datetime.now()},
    
    # Compliance
    {"question_text": "Is the project following the necessary financial regulations?", "category": "Compliance", "created_at": datetime.now()},
    {"question_text": "Has the project conducted proper KYC (Know Your Customer) checks?", "category": "Compliance", "created_at": datetime.now()},
    {"question_text": "Does the project follow anti-money laundering (AML) practices?", "category": "Compliance", "created_at": datetime.now()},
    
    # Ecology
    {"question_text": "What is the environmental impact of the project's operations?", "category": "Ecology", "created_at": datetime.now()},
    {"question_text": "Does the project take steps to reduce its carbon footprint?", "category": "Ecology", "created_at": datetime.now()},
    {"question_text": "Is the project using renewable energy sources for its operations?", "category": "Ecology", "created_at": datetime.now()},
    
    # Social
    {"question_text": "Does the project promote social good and community welfare?", "category": "Social", "created_at": datetime.now()},
    {"question_text": "Is the project transparent in its operations and funding?", "category": "Social", "created_at": datetime.now()},
    {"question_text": "Does the project have a fair policy on labor rights and human resources?", "category": "Social", "created_at": datetime.now()},
    
    # Governance
    {"question_text": "Is the project's governance structure transparent and decentralized?", "category": "Governance", "created_at": datetime.now()},
    {"question_text": "Does the project have a clear and effective decision-making process?", "category": "Governance", "created_at": datetime.now()},
    {"question_text": "Are the project's financial records open and audited regularly?", "category": "Governance", "created_at": datetime.now()},
]

# Insertion des questions dans MongoDB
questions_collection.insert_many(questions_data)

print("Questions insérées dans la base de données MongoDB.")

