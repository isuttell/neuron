import { vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test-utils';
import Personality from '../personality';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import type { PersonalityDocument } from '@/slices/personalitiesSlice.d';

// Mock dependencies
vi.mock('@/lib/api');
vi.mock('sonner');
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ personalityId: 'test-personality-id' }),
    useNavigate: () => vi.fn(),
  };
});

describe('Personality Component - Document Functionality', () => {
  const mockPersonality = {
    id: 'test-personality-id',
    name: 'Test Personality',
    description: 'Test description',
    context: 'Test context',
    memory: 'Test memory',
    logo: 'test-logo.png',
    tool_set: 'default',
    status: '',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  const mockDocuments: PersonalityDocument[] = [
    {
      id: 'doc-1',
      personality_id: 'test-personality-id',
      user_id: 'user-1',
      name: 'document1.txt',
      content: 'Content 1',
      doc_metadata: { chunk_ids: ['chunk1', 'chunk2'] },
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'doc-2',
      personality_id: 'test-personality-id',
      user_id: 'user-1',
      name: 'document2.md',
      content: 'Content 2',
      doc_metadata: { chunk_ids: ['chunk3', 'chunk4'] },
      created_at: '2024-01-01T00:00:00Z',
    },
  ];

  const initialState = {
    personalities: {
      personalities: [mockPersonality],
      personalityUsers: {},
      personalityDocuments: {
        'test-personality-id': mockDocuments,
      },
      loading: false,
      error: null,
      activePersonalityId: null,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock fetchPersonality response
    (api.get as vi.Mock).mockImplementation((url: string) => {
      if (url === '/personalities/test-personality-id') {
        return Promise.resolve({
          personality: mockPersonality,
          users: [],
          personality_users: [],
        });
      }
      if (url === '/personalities/test-personality-id/documents') {
        return Promise.resolve({
          personality_documents: mockDocuments,
        });
      }
      return Promise.resolve({});
    });
    (api.post as vi.Mock).mockResolvedValue({});
    (api.delete as vi.Mock).mockResolvedValue({});
  });

  describe('Document Display', () => {
    it('should display documents in a responsive grid', async () => {
      renderWithProviders(<Personality />, { preloadedState: initialState });

      // Wait for component to settle
      await waitFor(() => {
        expect(screen.getByText('document1.txt')).toBeInTheDocument();
      });

      // Check for grid container
      const gridContainer = screen.getByText('document1.txt').closest('.grid');
      expect(gridContainer).toHaveClass('grid-cols-1', 'sm:grid-cols-2', 'md:grid-cols-3', 'lg:grid-cols-4');

      // Check that documents are displayed
      expect(screen.getByText('document1.txt')).toBeInTheDocument();
      expect(screen.getByText('document2.md')).toBeInTheDocument();
    });

    it('should not display documents section when no documents exist', () => {
      const stateWithoutDocs = {
        ...initialState,
        personalities: {
          ...initialState.personalities,
          personalityDocuments: {
            'test-personality-id': [],
          },
        },
      };

      renderWithProviders(<Personality />, { preloadedState: stateWithoutDocs });

      // Grid should not be present
      expect(screen.queryByText('document1.txt')).not.toBeInTheDocument();
      expect(screen.queryByText('document2.md')).not.toBeInTheDocument();
    });
  });

  describe('Document Upload', () => {
    it('should handle single file upload', async () => {
      const user = userEvent.setup();
      (api.post as vi.Mock).mockResolvedValueOnce({
        personality_documents: [{
          id: 'doc-3',
          personality_id: 'test-personality-id',
          user_id: 'user-1',
          name: 'newdoc.txt',
          content: 'New content',
          doc_metadata: { chunk_ids: ['chunk5'] },
          created_at: '2024-01-03T00:00:00Z',
        }],
      });

      renderWithProviders(<Personality />, { preloadedState: initialState });

      // Find the hidden file input
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      expect(fileInput).toBeInTheDocument();
      expect(fileInput).toHaveAttribute('accept', '.txt,.md,.markdown');
      expect(fileInput).toHaveAttribute('multiple');

      // Create a test file
      const file = new File(['test content'], 'newdoc.txt', { type: 'text/plain' });

      // Simulate file selection
      await user.upload(fileInput, file);

      // Wait for API call
      await waitFor(() => {
        expect(api.post).toHaveBeenCalledWith(
          '/personalities/test-personality-id/documents',
          expect.any(FormData)
        );
      });

      // Check success toast
      expect(toast.success).toHaveBeenCalledWith('Document "newdoc.txt" uploaded successfully');
    });

    it('should handle multiple file upload', async () => {
      const user = userEvent.setup();
      (api.post as vi.Mock).mockResolvedValueOnce({
        personality_documents: [
          {
            id: 'doc-3',
            personality_id: 'test-personality-id',
            user_id: 'user-1',
            name: 'file1.txt',
            content: 'Content 1',
            doc_metadata: { chunk_ids: ['chunk5'] },
            created_at: '2024-01-03T00:00:00Z',
          },
          {
            id: 'doc-4',
            personality_id: 'test-personality-id',
            user_id: 'user-1',
            name: 'file2.md',
            content: 'Content 2',
            doc_metadata: { chunk_ids: ['chunk6'] },
            created_at: '2024-01-03T00:00:00Z',
          },
        ],
      });

      renderWithProviders(<Personality />, { preloadedState: initialState });

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

      // Create test files
      const files = [
        new File(['content 1'], 'file1.txt', { type: 'text/plain' }),
        new File(['content 2'], 'file2.md', { type: 'text/markdown' }),
      ];

      // Simulate file selection
      await user.upload(fileInput, files);

      await waitFor(() => {
        expect(api.post).toHaveBeenCalledWith(
          '/personalities/test-personality-id/documents',
          expect.any(FormData)
        );
      });

      expect(toast.success).toHaveBeenCalledWith('2 documents uploaded successfully');
    });

    it('should only accept valid file types', () => {
      renderWithProviders(<Personality />, { preloadedState: initialState });

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

      // Check that the file input has the correct accept attribute
      expect(fileInput).toHaveAttribute('accept', '.txt,.md,.markdown');
      expect(fileInput).toHaveAttribute('multiple');
    });

    it('should handle upload errors gracefully', async () => {
      const user = userEvent.setup();
      (api.post as vi.Mock).mockRejectedValueOnce(new Error('Upload failed'));

      renderWithProviders(<Personality />, { preloadedState: initialState });

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });

      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to upload documents');
      });
    });

    it('should trigger file input when upload button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Personality />, { preloadedState: initialState });

      // Find upload button by its icon (since it doesn't have visible text)
      const uploadButton = screen.getByRole('button', { name: /upload document/i });

      // Mock file input click
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const clickSpy = vi.spyOn(fileInput, 'click');

      await user.click(uploadButton);

      expect(clickSpy).toHaveBeenCalled();
    });
  });

  describe('Document Deletion', () => {
    it('should delete a document when delete button is clicked', async () => {
      const user = userEvent.setup();
      (api.delete as vi.Mock).mockResolvedValueOnce({});

      renderWithProviders(<Personality />, { preloadedState: initialState });

      // Find delete buttons (they're in each document card)
      const deleteButtons = screen.getAllByRole('button', { name: /delete document/i });
      expect(deleteButtons).toHaveLength(2);

      // Click the first delete button
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(api.delete).toHaveBeenCalledWith(
          '/personalities/test-personality-id/documents/doc-1'
        );
      });

      expect(toast.success).toHaveBeenCalledWith('Document "document1.txt" deleted');
    });

    it('should handle deletion errors gracefully', async () => {
      const user = userEvent.setup();
      (api.delete as vi.Mock).mockRejectedValueOnce(new Error('Delete failed'));

      renderWithProviders(<Personality />, { preloadedState: initialState });

      const deleteButtons = screen.getAllByRole('button', { name: /delete document/i });
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to delete document');
      });
    });
  });

  describe('UI States', () => {
    it('should disable upload button while uploading', async () => {
      const user = userEvent.setup();

      // Mock a slow upload
      (api.post as vi.Mock).mockImplementationOnce(
        () => new Promise(resolve => setTimeout(resolve, 100))
      );

      renderWithProviders(<Personality />, { preloadedState: initialState });

      const uploadButton = screen.getByRole('button', { name: /upload document/i });
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test'], 'test.txt', { type: 'text/plain' });

      // Start upload
      await user.upload(fileInput, file);

      // Button should be disabled during upload
      await waitFor(() => {
        expect(uploadButton).toBeDisabled();
      });

      // Wait for upload to complete
      await waitFor(() => {
        expect(uploadButton).not.toBeDisabled();
      });
    });

    it('should reset file input after successful upload', async () => {
      const user = userEvent.setup();
      (api.post as vi.Mock).mockResolvedValueOnce({
        personality_documents: [{
          id: 'doc-3',
          personality_id: 'test-personality-id',
          user_id: 'user-1',
          name: 'newdoc.txt',
          content: 'New content',
          doc_metadata: { chunk_ids: ['chunk5'] },
          created_at: '2024-01-03T00:00:00Z',
        }],
      });

      renderWithProviders(<Personality />, { preloadedState: initialState });

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const file = new File(['test content'], 'newdoc.txt', { type: 'text/plain' });

      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(fileInput.value).toBe('');
      });
    });
  });
});
