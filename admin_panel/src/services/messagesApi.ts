import { backendApi, backendApiFormData } from './api';

export interface Message {
  id: number;
  user_id: number;
  text: string;
  relevance: number | null;
  is_bot: number;
  created_at: string;
}

export interface SendMessageRequest {
  telegram_id: number;
  text: string;
  files?: File[];
}

export interface BroadcastRequest {
  telegram_ids: number[];
  text: string;
  files?: File[];
}

export interface ScheduleBroadcastRequest {
  telegram_ids: number[];
  text: string;
  scheduled_at: string;
  files?: File[];
}

export const messagesApi = {
  getUserMessages: async (telegramId: number): Promise<Message[]> => {
    const response = await backendApi.get<Message[]>(`/users/${telegramId}/messages`);
    return response.data;
  },

  sendMessage: async (request: SendMessageRequest): Promise<void> => {
    const formData = new FormData();
    formData.append('telegram_id', request.telegram_id.toString());
    formData.append('text', request.text);
    if (request.files && request.files.length > 0) {
      request.files.forEach((file) => {
        formData.append('files', file);
      });
    }
    await backendApiFormData.post('/admin/send-message', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  broadcast: async (request: BroadcastRequest): Promise<void> => {
    const formData = new FormData();
    formData.append('telegram_ids', JSON.stringify(request.telegram_ids));
    formData.append('text', request.text);
    if (request.files && request.files.length > 0) {
      request.files.forEach((file) => {
        formData.append('files', file);
      });
    }
    await backendApiFormData.post('/admin/broadcast', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  scheduleBroadcast: async (request: ScheduleBroadcastRequest): Promise<void> => {
    const formData = new FormData();
    formData.append('telegram_ids', JSON.stringify(request.telegram_ids));
    formData.append('text', request.text);
    formData.append('scheduled_at', request.scheduled_at);
    if (request.files && request.files.length > 0) {
      request.files.forEach((file) => {
        formData.append('files', file);
      });
    }
    await backendApiFormData.post('/admin/schedule-broadcast', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

