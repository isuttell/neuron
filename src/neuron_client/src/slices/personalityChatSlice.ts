import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice, createSelector } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import {
  fetchPersonalityMessages,
  loadMorePersonalityMessages,
  sendPersonalityMessage,
  updatePersonalityMessage,
  deletePersonalityMessage,
  clearPersonalityMessages,
} from "../actions/personalityChatActions";
import type {
  PersonalityMessage,
  PersonalityChatState,
  OptimisticPersonalityMessage,
  PersonalityChatMessage,
  PersonalityChatMessageEvent,
  PersonalityChatUpdateEvent,
  PersonalityChatDeleteEvent,
  PersonalityMessagesResponse,
  CreatePersonalityMessageResponse,
  UpdatePersonalityMessageResponse,
} from "../types/personalityChat";

// Action payload types for extraReducers
interface FetchPersonalityMessagesPayload extends PersonalityMessagesResponse {
  personalityId: string;
  hasMore: boolean;
}

interface LoadMorePersonalityMessagesPayload extends PersonalityMessagesResponse {
  personalityId: string;
  hasMore: boolean;
}

interface SendPersonalityMessagePayload extends CreatePersonalityMessageResponse {
  personality_message: PersonalityMessage & { temp_id?: string };
}

interface DeletePersonalityMessagePayload {
  messageId: string;
  personalityId: string;
}

// Initial state following the established pattern
const initialState: PersonalityChatState = {
  messageMap: {},
  messageIds: [],
  activePersonalityId: null,
  loading: false,
  error: null,
  hasMore: {},
  loadingMore: {},
};

/**
 * Helper function to upsert a personality message into the state
 */
function upsert(state: PersonalityChatState, message: PersonalityChatMessage) {
  const messageId = message.id;

  if (!state.messageMap[messageId]) {
    // Add to the end to maintain chronological order (oldest first, newest at bottom)
    state.messageIds.push(messageId);
  }
  state.messageMap[messageId] = message;
}

export const personalityChatSlice = createSlice({
  name: "personalityChat",
  initialState,
  reducers: {
    setActivePersonalityId: (
      state,
      action: PayloadAction<string | null>
    ) => {
      state.activePersonalityId = action.payload;
    },

    addOptimisticMessage: (
      state,
      action: PayloadAction<{
        tempId: string;
        content: string;
        personalityId: string;
        roomId: string;
        userId: string;
      }>
    ) => {
      const { tempId, content, personalityId, roomId, userId } = action.payload;
      const optimisticMessage: OptimisticPersonalityMessage = {
        id: tempId,
        tempId,
        personality_id: personalityId,
        personality_room_id: roomId,
        user_id: userId,
        content,
        created_at: Date.now(),
        updated_at: Date.now(),
        thread_id: null,
        isOptimistic: true,
        media_items: [],
      };

      state.messageIds.push(tempId);
      state.messageMap[tempId] = optimisticMessage;
    },

    markMessageFailed: (
      state,
      action: PayloadAction<{ tempId: string; error: string }>
    ) => {
      const { tempId, error } = action.payload;
      const message = state.messageMap[tempId];
      if (message && 'isOptimistic' in message) {
        message.error = error;
        message.isOptimistic = false;
      }
    },

    removeOptimisticMessage: (state, action: PayloadAction<string>) => {
      const tempId = action.payload;
      delete state.messageMap[tempId];
      state.messageIds = state.messageIds.filter((id) => id !== tempId);
    },

    upsertMessage: (
      state,
      action: PayloadAction<PersonalityChatMessageEvent>
    ) => {
      const incomingMessage = action.payload.message;

      // Check if we have an optimistic message to replace
      const tempId = (incomingMessage as PersonalityMessage & { temp_id?: string }).temp_id;
      if (tempId) {
        // Remove the optimistic message
        const optimisticIndex = state.messageIds.indexOf(tempId);
        if (optimisticIndex !== -1) {
          state.messageIds.splice(optimisticIndex, 1);
          delete state.messageMap[tempId];
        }
      }

      upsert(state, incomingMessage);
    },

    upsertMessages: (
      state,
      action: PayloadAction<{ messages: PersonalityMessage[]; personalityId: string; hasMore?: boolean }>
    ) => {
      const { messages, personalityId, hasMore = false } = action.payload;

      for (const message of messages) {
        upsert(state, message);
      }

      // Update pagination state
      state.hasMore[personalityId] = hasMore;
      state.loadingMore[personalityId] = false;
    },

    updateMessage: (
      state,
      action: PayloadAction<PersonalityChatUpdateEvent>
    ) => {
      const updatedMessage = action.payload.message;
      const messageId = updatedMessage.id;

      if (state.messageMap[messageId]) {
        state.messageMap[messageId] = updatedMessage;
      }
    },

    deleteMessage: (
      state,
      action: PayloadAction<PersonalityChatDeleteEvent>
    ) => {
      const { message_id } = action.payload;
      delete state.messageMap[message_id];
      state.messageIds = state.messageIds.filter((id) => id !== message_id);
    },

    setLoadingMore: (
      state,
      action: PayloadAction<{ personalityId: string; loading: boolean }>
    ) => {
      const { personalityId, loading } = action.payload;
      state.loadingMore[personalityId] = loading;
    },

    clearMessages: (state, action: PayloadAction<string>) => {
      const personalityId = action.payload;
      // Remove all messages for the specified personality
      const messagesToRemove = state.messageIds.filter(
        (id) => state.messageMap[id]?.personality_id === personalityId
      );

      messagesToRemove.forEach((id) => {
        delete state.messageMap[id];
      });

      state.messageIds = state.messageIds.filter(
        (id) => !messagesToRemove.includes(id)
      );

      // Reset pagination state
      delete state.hasMore[personalityId];
      delete state.loadingMore[personalityId];
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch personality messages
      .addCase(fetchPersonalityMessages.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        fetchPersonalityMessages.fulfilled,
        (state, action: PayloadAction<FetchPersonalityMessagesPayload>) => {
          state.loading = false;
          const { personality_messages, personalityId, hasMore } = action.payload;

          // Clear existing messages for this personality before adding new ones
          const messagesToRemove = state.messageIds.filter(
            (id) => state.messageMap[id]?.personality_id === personalityId
          );

          messagesToRemove.forEach((id) => {
            delete state.messageMap[id];
          });

          state.messageIds = state.messageIds.filter(
            (id) => !messagesToRemove.includes(id)
          );

          // Add new messages
          for (const message of personality_messages) {
            upsert(state, message);
          }

          // Update pagination state
          state.hasMore[personalityId] = hasMore;
          state.loadingMore[personalityId] = false;
        }
      )
      .addCase(fetchPersonalityMessages.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch personality messages";
      })

      // Load more personality messages
      .addCase(
        loadMorePersonalityMessages.fulfilled,
        (state, action: PayloadAction<LoadMorePersonalityMessagesPayload>) => {
          const { personality_messages, personalityId, hasMore } = action.payload;

          // Add new messages (append to existing)
          for (const message of personality_messages) {
            upsert(state, message);
          }

          // Update pagination state
          state.hasMore[personalityId] = hasMore;
          state.loadingMore[personalityId] = false;
        }
      )
      .addCase(loadMorePersonalityMessages.rejected, (state, action) => {
        state.error = action.error.message || "Failed to load more messages";
      })

      // Send personality message
      .addCase(
        sendPersonalityMessage.fulfilled,
        (state, action: PayloadAction<SendPersonalityMessagePayload>) => {
          const incomingMessage = action.payload.personality_message;

          // Check if we have an optimistic message to replace
          const tempId = incomingMessage.temp_id;
          if (tempId) {
            // Remove the optimistic message
            const optimisticIndex = state.messageIds.indexOf(tempId);
            if (optimisticIndex !== -1) {
              state.messageIds.splice(optimisticIndex, 1);
              delete state.messageMap[tempId];
            }
          }

          upsert(state, incomingMessage);
        }
      )

      // Update personality message
      .addCase(
        updatePersonalityMessage.fulfilled,
        (state, action: PayloadAction<UpdatePersonalityMessageResponse>) => {
          const updatedMessage = action.payload.personality_message;
          const messageId = updatedMessage.id;

          if (state.messageMap[messageId]) {
            state.messageMap[messageId] = updatedMessage;
          }
        }
      )

      // Delete personality message
      .addCase(
        deletePersonalityMessage.fulfilled,
        (state, action: PayloadAction<DeletePersonalityMessagePayload>) => {
          const { messageId } = action.payload;
          delete state.messageMap[messageId];
          state.messageIds = state.messageIds.filter((id) => id !== messageId);
        }
      )

      // Clear personality messages
      .addCase(
        clearPersonalityMessages.fulfilled,
        (state, action: PayloadAction<string>) => {
          const personalityId = action.payload;
          // Remove all messages for the specified personality
          const messagesToRemove = state.messageIds.filter(
            (id) => state.messageMap[id]?.personality_id === personalityId
          );

          messagesToRemove.forEach((id) => {
            delete state.messageMap[id];
          });

          state.messageIds = state.messageIds.filter(
            (id) => !messagesToRemove.includes(id)
          );

          // Reset pagination state
          delete state.hasMore[personalityId];
          delete state.loadingMore[personalityId];
        }
      );
  },
});

export const {
  setActivePersonalityId,
  addOptimisticMessage,
  markMessageFailed,
  removeOptimisticMessage,
  upsertMessage,
  upsertMessages,
  updateMessage,
  deleteMessage,
  setLoadingMore,
  clearMessages,
} = personalityChatSlice.actions;

// Base selectors
const selectPersonalityChatState = (state: RootState) => state.personalityChat;
const selectMessageIds = (state: RootState) => state.personalityChat.messageIds;
const selectMessageMap = (state: RootState) => state.personalityChat.messageMap;

// Memoized selectors following established patterns
export const getPersonalityChatLoading = createSelector(
  [selectPersonalityChatState],
  (state) => state.loading
);

export const getPersonalityChatError = createSelector(
  [selectPersonalityChatState],
  (state) => state.error
);

export const getActivePersonalityId = createSelector(
  [selectPersonalityChatState],
  (state) => state.activePersonalityId
);

export const getAllPersonalityChatMessages = createSelector(
  [selectMessageIds, selectMessageMap],
  (messageIds, messageMap) => messageIds.map((id) => messageMap[id])
);

export const getPersonalityChatMessage = createSelector(
  [selectMessageMap, (_, id: string) => id],
  (messageMap, id) => messageMap[id]
);

export const getPersonalityChatMessages = createSelector(
  [getAllPersonalityChatMessages, (_, personalityId?: string) => personalityId],
  (messages, personalityId) =>
    messages
      .filter((message) =>
        personalityId ? message.personality_id === personalityId : true
      )
      .sort((a, b) => {
        // Sort by created_at timestamp to ensure stable chronological order
        const aTime = typeof a.created_at === 'number' ? a.created_at : new Date(a.created_at).getTime();
        const bTime = typeof b.created_at === 'number' ? b.created_at : new Date(b.created_at).getTime();
        return aTime - bTime;
      })
);

export const getPersonalityChatHasMore = createSelector(
  [selectPersonalityChatState, (_, personalityId: string) => personalityId],
  (state, personalityId) => state.hasMore[personalityId] || false
);

export const getPersonalityChatLoadingMore = createSelector(
  [selectPersonalityChatState, (_, personalityId: string) => personalityId],
  (state, personalityId) => state.loadingMore[personalityId] || false
);

// Selector for active personality messages
export const getActivePersonalityMessages = createSelector(
  [getAllPersonalityChatMessages, getActivePersonalityId],
  (messages, activePersonalityId) =>
    activePersonalityId
      ? messages.filter((message) => message.personality_id === activePersonalityId)
      : []
);

// Selector for messages by personality and room
export const getPersonalityChatMessagesByRoom = createSelector(
  [getAllPersonalityChatMessages, (_, personalityId?: string, roomId?: string) => ({ personalityId, roomId })],
  (messages, { personalityId, roomId }) =>
    messages
      .filter((message) => {
        const matchesPersonality = personalityId ? message.personality_id === personalityId : true;
        const matchesRoom = roomId ? message.personality_room_id === roomId : true;
        return matchesPersonality && matchesRoom;
      })
      .sort((a, b) => {
        const aTime = typeof a.created_at === 'number' ? a.created_at : new Date(a.created_at).getTime();
        const bTime = typeof b.created_at === 'number' ? b.created_at : new Date(b.created_at).getTime();
        return aTime - bTime;
      })
);


export default personalityChatSlice.reducer;
