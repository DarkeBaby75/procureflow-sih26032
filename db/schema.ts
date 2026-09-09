import { index, sqliteTable, text } from 'drizzle-orm/sqlite-core';

export const chatConversations = sqliteTable('chat_conversations', {
  id: text('id').primaryKey(),
  participantId: text('participant_id').notNull(),
  participantName: text('participant_name').notNull(),
  participantRole: text('participant_role').notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
}, table => [index('idx_chat_conversations_updated').on(table.updatedAt)]);

export const chatMessages = sqliteTable('chat_messages', {
  id: text('id').primaryKey(),
  conversationId: text('conversation_id').notNull(),
  senderId: text('sender_id').notNull(),
  senderName: text('sender_name').notNull(),
  senderRole: text('sender_role').notNull(),
  body: text('body').notNull(),
  mediaKey: text('media_key'),
  mediaName: text('media_name'),
  mediaType: text('media_type'),
  createdAt: text('created_at').notNull(),
  editedAt: text('edited_at'),
  deletedAt: text('deleted_at'),
  seenAt: text('seen_at'),
}, table => [index('idx_chat_messages_conversation').on(table.conversationId, table.createdAt)]);

export const userAccounts = sqliteTable('user_accounts', {
  id: text('id').primaryKey(),
  role: text('role').notNull(),
  fullName: text('full_name').notNull(),
  email: text('email').notNull().unique(),
  phone: text('phone').notNull(),
  location: text('location').notNull(),
  status: text('status').notNull(),
  passwordSalt: text('password_salt').notNull(),
  passwordHash: text('password_hash').notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
}, table => [index('idx_user_accounts_role_status').on(table.role, table.status)]);

export const authSessions = sqliteTable('auth_sessions', {
  token: text('token').primaryKey(),
  userId: text('user_id').notNull(),
  userName: text('user_name').notNull(),
  userEmail: text('user_email').notNull(),
  role: text('role').notNull(),
  expiresAt: text('expires_at').notNull(),
  createdAt: text('created_at').notNull(),
}, table => [index('idx_auth_sessions_expiry').on(table.expiresAt)]);
