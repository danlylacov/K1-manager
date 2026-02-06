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

export interface AdminUser {
  id: number;
  username: string;
  role: string;
  created_at: string;
}

export interface AdminUserCreate {
  username: string;
  password: string;
  role: string;
}

export interface AdminUserUpdate {
  username?: string;
  password?: string;
  role?: string;
}

export const adminUsersApi = {
  getAll: async (): Promise<AdminUser[]> => {
    const response = await backendApi.get<AdminUser[]>('/admin/users');
    return response.data;
  },

  create: async (user: AdminUserCreate): Promise<AdminUser> => {
    const response = await backendApi.post<AdminUser>('/admin/users', user);
    return response.data;
  },

  update: async (id: number, user: AdminUserUpdate): Promise<AdminUser> => {
    const response = await backendApi.put<AdminUser>(`/admin/users/${id}`, user);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await backendApi.delete(`/admin/users/${id}`);
  },
};

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

