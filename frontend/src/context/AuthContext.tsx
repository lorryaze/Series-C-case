import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { authService } from '../services/authService';
import { tokenStorage } from '../services/apiClient';
import type { Role, User } from '../types';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  /** True when the user's role is one of ``roles``. */
  hasRole: (...roles: Role[]) => boolean;
  /** Reviewers and admins may act on KYC cases and refunds. */
  canReview: boolean;
  /** Only admins may administer feature flags and users. */
  canAdminister: boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }): JSX.Element {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!tokenStorage.read()) {
      setIsLoading(false);
      return;
    }
    authService
      .me()
      .then(setUser)
      .catch(() => tokenStorage.clear())
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authService.login(email, password);
    setUser(response.user);
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => {
    const hasRole = (...roles: Role[]) => (user ? roles.includes(user.role) : false);
    return {
      user,
      isLoading,
      login,
      logout,
      hasRole,
      canReview: hasRole('admin', 'reviewer'),
      canAdminister: hasRole('admin'),
    };
  }, [user, isLoading, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider');
  }
  return context;
}
