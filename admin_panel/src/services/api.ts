import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || '/api';
const RAG_API_URL = import.meta.env.VITE_RAG_API_URL || '/rag-api';

export const backendApi = axios.create({
  baseURL: BACKEND_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Для поддержки сессий (cookies)
});

export const ragApi = axios.create({
  baseURL: RAG_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 секунд таймаут для RAG API
});

// Для загрузки файлов
export const backendApiFormData = axios.create({
  baseURL: BACKEND_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
  withCredentials: true, // Для поддержки сессий (cookies)
});

export const ragApiFormData = axios.create({
  baseURL: RAG_API_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
  timeout: 120000, // 2 минуты для загрузки файлов
});

