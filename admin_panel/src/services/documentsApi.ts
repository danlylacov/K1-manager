import { ragApi, ragApiFormData } from './api';

export interface Document {
  document: string;
  chunks: number;
}

export interface DocumentsResponse {
  documents: Document[];
  total_documents: number;
  total_chunks: number;
}

export const documentsApi = {
  getAll: async (): Promise<DocumentsResponse> => {
    const response = await ragApi.get<DocumentsResponse>('/documents');
    return response.data;
  },

  upload: async (file: File, replaceAll: boolean = true): Promise<void> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('replace_all', replaceAll.toString());
    await ragApiFormData.post('/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  update: async (documentName: string, file: File): Promise<void> => {
    const formData = new FormData();
    formData.append('file', file);
    await ragApiFormData.put(`/documents/${encodeURIComponent(documentName)}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  delete: async (documentName: string): Promise<void> => {
    await ragApi.delete(`/documents/${encodeURIComponent(documentName)}`);
  },
};

