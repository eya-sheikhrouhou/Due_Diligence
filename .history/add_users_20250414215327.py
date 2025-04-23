from pymongo import MongoClient
import bcrypt

client = MongoClient("mongodb://localhost:27017/")
db = client["due_diligence"]

email = "admin@example.com"
password = "admin123"
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

db["users"].insert_one({
    "email": email,
    "password": hashed
})