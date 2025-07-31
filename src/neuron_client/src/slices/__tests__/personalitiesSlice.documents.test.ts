import { vi } from 'vitest';
import personalitiesReducer, {
  addPersonalityDocuments,
  PersonalityState,
} from '../personalitiesSlice';
import { fetchPersonalityDocuments, deletePersonalityDocument } from '@/actions/personalityActions';
import type { PersonalityDocument } from '../personalitiesSlice.d';

describe('personalitiesSlice - document functionality', () => {
  const initialState: PersonalityState = {
    personalities: [],
    personalityUsers: {},
    personalityDocuments: {},
    loading: false,
    error: null,
    activePersonalityId: null,
  };

  const mockDocument1: PersonalityDocument = {
    id: 'doc-1',
    personality_id: 'personality-1',
    user_id: 'user-1',
    name: 'document1.txt',
    content: 'Test content 1',
    doc_metadata: { chunk_ids: ['chunk1', 'chunk2'] },
    created_at: '2024-01-01T00:00:00Z',
  };

  const mockDocument2: PersonalityDocument = {
    id: 'doc-2',
    personality_id: 'personality-1',
    user_id: 'user-1',
    name: 'document2.md',
    content: 'Test content 2',
    doc_metadata: { chunk_ids: ['chunk3', 'chunk4'] },
    created_at: '2024-01-02T00:00:00Z',
  };

  const mockDocument3: PersonalityDocument = {
    id: 'doc-3',
    personality_id: 'personality-1',
    user_id: 'user-1',
    name: 'document3.txt',
    content: 'Test content 3',
    doc_metadata: { chunk_ids: ['chunk5'] },
    created_at: '2024-01-03T00:00:00Z',
  };

  describe('addPersonalityDocuments', () => {
    it('should add documents to empty state', () => {
      const action = addPersonalityDocuments({
        personalityId: 'personality-1',
        documents: [mockDocument1, mockDocument2],
      });

      const newState = personalitiesReducer(initialState, action);

      expect(newState.personalityDocuments['personality-1']).toHaveLength(2);
      expect(newState.personalityDocuments['personality-1']).toEqual([
        mockDocument1,
        mockDocument2,
      ]);
    });

    it('should prepend new documents to existing documents', () => {
      const stateWithDocuments: PersonalityState = {
        ...initialState,
        personalityDocuments: {
          'personality-1': [mockDocument1],
        },
      };

      const action = addPersonalityDocuments({
        personalityId: 'personality-1',
        documents: [mockDocument2, mockDocument3],
      });

      const newState = personalitiesReducer(stateWithDocuments, action);

      expect(newState.personalityDocuments['personality-1']).toHaveLength(3);
      expect(newState.personalityDocuments['personality-1']).toEqual([
        mockDocument2,
        mockDocument3,
        mockDocument1,
      ]);
    });

    it('should create new personality document array if not exists', () => {
      const action = addPersonalityDocuments({
        personalityId: 'personality-2',
        documents: [mockDocument1],
      });

      const newState = personalitiesReducer(initialState, action);

      expect(newState.personalityDocuments['personality-2']).toBeDefined();
      expect(newState.personalityDocuments['personality-2']).toHaveLength(1);
      expect(newState.personalityDocuments['personality-2'][0]).toEqual(mockDocument1);
    });

    it('should handle empty documents array', () => {
      const action = addPersonalityDocuments({
        personalityId: 'personality-1',
        documents: [],
      });

      const newState = personalitiesReducer(initialState, action);

      expect(newState.personalityDocuments['personality-1']).toEqual([]);
    });
  });

  describe('fetchPersonalityDocuments', () => {
    it('should handle fetchPersonalityDocuments.fulfilled', () => {
      const payload = {
        personalityId: 'personality-1',
        personality_documents: [mockDocument1, mockDocument2],
      };
      const action = {
        type: fetchPersonalityDocuments.fulfilled.type,
        payload,
      };

      const newState = personalitiesReducer(initialState, action);

      expect(newState.personalityDocuments['personality-1']).toEqual([
        mockDocument1,
        mockDocument2,
      ]);
    });

    it('should replace existing documents on fulfilled', () => {
      const stateWithDocuments: PersonalityState = {
        ...initialState,
        personalityDocuments: {
          'personality-1': [mockDocument3],
        },
      };

      const payload = {
        personalityId: 'personality-1',
        personality_documents: [mockDocument1, mockDocument2],
      };
      const action = {
        type: fetchPersonalityDocuments.fulfilled.type,
        payload,
      };

      const newState = personalitiesReducer(stateWithDocuments, action);

      expect(newState.personalityDocuments['personality-1']).toEqual([
        mockDocument1,
        mockDocument2,
      ]);
      expect(newState.personalityDocuments['personality-1']).not.toContain(mockDocument3);
    });
  });

  describe('deletePersonalityDocument', () => {
    it('should handle deletePersonalityDocument.fulfilled', () => {
      const stateWithDocuments: PersonalityState = {
        ...initialState,
        personalityDocuments: {
          'personality-1': [mockDocument1, mockDocument2, mockDocument3],
        },
      };

      const action = {
        type: deletePersonalityDocument.fulfilled.type,
        payload: {
          personalityId: 'personality-1',
          documentId: 'doc-2',
        },
      };

      const newState = personalitiesReducer(stateWithDocuments, action);

      expect(newState.personalityDocuments['personality-1']).toHaveLength(2);
      expect(newState.personalityDocuments['personality-1']).toEqual([
        mockDocument1,
        mockDocument3,
      ]);
      expect(newState.personalityDocuments['personality-1']).not.toContainEqual(
        expect.objectContaining({ id: 'doc-2' })
      );
    });

    it('should handle deleting non-existent document', () => {
      const stateWithDocuments: PersonalityState = {
        ...initialState,
        personalityDocuments: {
          'personality-1': [mockDocument1, mockDocument2],
        },
      };

      const action = {
        type: deletePersonalityDocument.fulfilled.type,
        payload: {
          personalityId: 'personality-1',
          documentId: 'doc-999',
        },
      };

      const newState = personalitiesReducer(stateWithDocuments, action);

      expect(newState.personalityDocuments['personality-1']).toHaveLength(2);
      expect(newState.personalityDocuments['personality-1']).toEqual([
        mockDocument1,
        mockDocument2,
      ]);
    });

    it('should handle deleting from non-existent personality', () => {
      const action = {
        type: deletePersonalityDocument.fulfilled.type,
        payload: {
          personalityId: 'personality-999',
          documentId: 'doc-1',
        },
      };

      const newState = personalitiesReducer(initialState, action);

      expect(newState.personalityDocuments['personality-999']).toBeUndefined();
    });
  });

  describe('selector: getPersonalityDocuments', () => {
    it('should return documents for a personality', () => {
      const state: PersonalityState = {
        ...initialState,
        personalityDocuments: {
          'personality-1': [mockDocument1, mockDocument2],
          'personality-2': [mockDocument3],
        },
      };

      const result = state.personalityDocuments['personality-1'] || [];
      expect(result).toEqual([mockDocument1, mockDocument2]);
    });

    it('should return empty array for personality without documents', () => {
      const result = initialState.personalityDocuments['personality-999'] || [];
      expect(result).toEqual([]);
    });
  });
});
