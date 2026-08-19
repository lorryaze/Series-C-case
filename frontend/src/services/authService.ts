import { request, tokenStorage } from './apiClient';
import type { LoginResponse, User } from '../types';

export const authService = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    tokenStorage.write(response.access_token);
    tokenStorage.writeRefresh(response.refresh_token);
    return response;
  },

  me(): Promise<User> {
    return request<User>('/auth/me');
  },

  users(): Promise<User[]> {
    return request<User[]>('/auth/users');
  },

  logout(): void {
    tokenStorage.clear();
  },
};
