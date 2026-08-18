import { useQuery } from '@tanstack/react-query';
import { authService } from '../services/authService';
import type { User } from '../types';

/** Staff directory, used to populate reviewer assignment pickers. */
export function useReviewers(enabled = true) {
  return useQuery<User[], Error, User[]>({
    queryKey: ['users'],
    queryFn: () => authService.users(),
    enabled,
    select: (users) => users.filter((user) => user.role !== 'viewer'),
    staleTime: 5 * 60 * 1000,
  });
}
