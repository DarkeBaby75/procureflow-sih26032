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
