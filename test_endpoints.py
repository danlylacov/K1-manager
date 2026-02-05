#!/usr/bin/env python3
"""Скрипт для тестирования всех эндпоинтов"""
import requests
import json

RAG_API_URL = "http://localhost:8000"
BACKEND_API_URL = "http://localhost:8001"

def test_rag_api():
    print("=" * 50)
    print("Тестирование RAG API")
    print("=" * 50)
    
    # GET /
    try:
        r = requests.get(f"{RAG_API_URL}/")
        print(f"GET /: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"GET /: ERROR - {e}")
    
    # POST /query
    try:
        r = requests.post(f"{RAG_API_URL}/query", json={"question": "Сколько стоит обучение?"})
        print(f"POST /query: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Question: {data.get('question')}")
            print(f"  Relevance: {data.get('avg_similirity')}")
            print(f"  Answer length: {len(data.get('llm_answer', ''))}")
        else:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"POST /query: ERROR - {e}")
    
    # GET /documents
    try:
        r = requests.get(f"{RAG_API_URL}/documents")
        print(f"GET /documents: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"GET /documents: ERROR - {e}")


def test_backend_api():
    print("\n" + "=" * 50)
    print("Тестирование Backend API")
    print("=" * 50)
    
    # GET /
    try:
        r = requests.get(f"{BACKEND_API_URL}/")
        print(f"GET /: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"GET /: ERROR - {e}")
    
    # GET /users
    try:
        r = requests.get(f"{BACKEND_API_URL}/users")
        print(f"GET /users: {r.status_code}")
        if r.status_code == 200:
            users = r.json()
            print(f"  Total users: {len(users)}")
        else:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"GET /users: ERROR - {e}")
    
    # POST /users
    try:
        test_user = {
            "telegram_id": 999999999,
            "username": "test_user"
        }
        r = requests.post(f"{BACKEND_API_URL}/users", json=test_user)
        print(f"POST /users: {r.status_code}")
        if r.status_code == 200:
            print(f"  Created user ID: {r.json().get('id')}")
        else:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"POST /users: ERROR - {e}")
    
    # GET /users/{telegram_id}
    try:
        r = requests.get(f"{BACKEND_API_URL}/users/999999999")
        print(f"GET /users/999999999: {r.status_code}")
        if r.status_code == 200:
            print(f"  User: {r.json().get('username')}")
        else:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"GET /users/{{telegram_id}}: ERROR - {e}")
    
    # POST /query
    try:
        r = requests.post(f"{BACKEND_API_URL}/query", json={
            "telegram_id": 999999999,
            "question": "Тестовый вопрос"
        })
        print(f"POST /query: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Question: {data.get('question')}")
            print(f"  Relevance: {data.get('relevance')}")
            print(f"  Answer length: {len(data.get('answer', ''))}")
        else:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"POST /query: ERROR - {e}")
    
    # GET /messages
    try:
        r = requests.get(f"{BACKEND_API_URL}/messages?user_id=1")
        print(f"GET /messages?user_id=1: {r.status_code}")
        if r.status_code == 200:
            messages = r.json()
            print(f"  Total messages: {len(messages)}")
        else:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"GET /messages: ERROR - {e}")


if __name__ == "__main__":
    test_rag_api()
    test_backend_api()
    print("\n" + "=" * 50)
    print("Тестирование завершено")
    print("=" * 50)

