import { backendApi } from './api';

export interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  phone: string | null;
  created_at: string;
  mouse_keyboard_skill: string | null;
  programming_experience: string | null;
  child_age: number | null;
  child_name: string | null;
  onboarding_completed: number;
}

export interface OnboardingData {
  extracted: {
    mouse_keyboard_skill: string | null;
    programming_experience: string | null;
    child_age: number | null;
    child_name: string | null;
  };
  needs_clarification: boolean;
  clarification_question: string | null;
}

export const usersApi = {
  getAll: async (): Promise<User[]> => {
    const response = await backendApi.get<User[]>('/users');
    return response.data;
  },

  getById: async (telegramId: number): Promise<User> => {
    const response = await backendApi.get<User>(`/users/${telegramId}`);
    return response.data;
  },

  getOnboardingData: async (telegramId: number): Promise<OnboardingData> => {
    const response = await backendApi.get<OnboardingData>(`/users/${telegramId}/onboarding/data`);
    return response.data;
  },
};

