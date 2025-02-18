# test.py
from pymongo import MongoClient

def test_mongodb_connection():
    try:
        client = MongoClient('mongodb://wolfgameuser:wolfgamepassword@localhost:27017/wolf_game_mongo_db')
        print("Available databases:")
        print(client.list_database_names())
        print("MongoDB connection successful!")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")

if __name__ == "__main__":
    test_mongodb_connection()