import { backendApi } from './api';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  username: string;
  role: string;
  message: string;
}

export interface CurrentUser {
  username: string;
  role: string;
}

export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await backendApi.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await backendApi.post('/auth/logout');
  },

  getCurrentUser: async (): Promise<CurrentUser> => {
    const response = await backendApi.get<CurrentUser>('/auth/me');
    return response.data;
  },
};

