export type ErrorCode =
  | 'booking_conflict'
  | 'forbidden'
  | 'not_found'
  | 'validation_error';

export interface Booking {
  id: string;
  sessionId: string;
  userId: string;
  status: 'confirmed' | 'waitlisted' | 'checked_in' | 'cancelled';
  createdAt: string;
  checkedInAt?: string;
}

export interface Session {
  id: string;
  title: string;
  capacity: number;
  attendeeCount: number;
  waitlistCount: number;
  createdBy: string;
}

export interface User {
  id: string;
  displayName: string | null;
}

export interface AuthApi {
  register(displayName: string, email: string, password: string): Promise<User>;
  login(email: string, password: string): Promise<User>;
  logout(): Promise<void>;
  me(): Promise<User | null>;
}

export interface SessionApi {
  list(): Promise<Session[]>;
  get(id: string): Promise<Session | null>;
  create(title: string, capacity: number): Promise<Session>;
  cancel(id: string): Promise<Session>;
  book(id: string): Promise<Booking>;
  cancelBooking(bookingId: string): Promise<Booking>;
  checkIn(bookingId: string): Promise<Booking>;
  getRoster(id: string): Promise<Booking[]>;
}

export interface Api {
  auth: AuthApi;
  sessions: SessionApi;
}