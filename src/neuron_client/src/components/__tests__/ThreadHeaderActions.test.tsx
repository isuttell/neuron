import { vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ThreadHeaderActions from '../ThreadHeaderActions';
import { TooltipProvider } from '@/components/ui/tooltip';

// Mock the useThreadPermissions hook
vi.mock('@/hooks/useThreadPermissions', () => ({
  useThreadPermissions: vi.fn(() => ({
    canManage: true,
    canManageUsers: true,
    canDelete: true,
    canViewSystemMessages: true,
    shouldShowComponent: true,
  })),
}));

import { useThreadPermissions } from '@/hooks/useThreadPermissions';
const mockUseThreadPermissions = vi.mocked(useThreadPermissions);

describe('ThreadHeaderActions', () => {
  const mockProps = {
    threadId: 'test-thread-id',
    showTools: false,
    onToggleTools: vi.fn(),
    onEditPersonality: vi.fn(),
    onManageUsers: vi.fn(),
    onDeleteThread: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (props = mockProps) => {
    return render(
      <TooltipProvider>
        <ThreadHeaderActions {...props} />
      </TooltipProvider>
    );
  };

  it('renders the dropdown trigger button', () => {
    renderComponent();

    const trigger = screen.getByRole('button', { name: /more actions/i });
    expect(trigger).toBeInTheDocument();
  });

  it('opens dropdown menu when clicked', async () => {
    const user = userEvent.setup();
    renderComponent();

    const trigger = screen.getByRole('button', { name: /more actions/i });
    await user.click(trigger);

    // Check all menu items are visible
    expect(screen.getByText(/show system messages/i)).toBeInTheDocument();
    expect(screen.getByText(/edit personality/i)).toBeInTheDocument();
    expect(screen.getByText(/manage users/i)).toBeInTheDocument();
    expect(screen.getByText(/delete thread/i)).toBeInTheDocument();
  });

  it('shows correct text for system messages toggle based on showTools prop', async () => {
    const user = userEvent.setup();
    const { rerender } = renderComponent({ ...mockProps, showTools: false });

    const trigger = screen.getByRole('button', { name: /more actions/i });
    await user.click(trigger);

    expect(screen.getByText(/show system messages/i)).toBeInTheDocument();

    // Close dropdown by pressing Escape
    await user.keyboard('{Escape}');

    // Rerender with showTools true
    rerender(
      <TooltipProvider>
        <ThreadHeaderActions {...mockProps} showTools={true} />
      </TooltipProvider>
    );
    await user.click(trigger);

    expect(screen.getByText(/hide system messages/i)).toBeInTheDocument();
  });

  it('calls onToggleTools when system messages item is clicked', async () => {
    const user = userEvent.setup();
    renderComponent();

    const trigger = screen.getByRole('button', { name: /more actions/i });
    await user.click(trigger);

    const toggleItem = screen.getByText(/show system messages/i);
    await user.click(toggleItem);

    expect(mockProps.onToggleTools).toHaveBeenCalledTimes(1);
  });

  it('calls onEditPersonality when edit personality item is clicked', async () => {
    const user = userEvent.setup();
    renderComponent();

    const trigger = screen.getByRole('button', { name: /more actions/i });
    await user.click(trigger);

    const editItem = screen.getByText(/edit personality/i);
    await user.click(editItem);

    // Wait for the setTimeout to execute
    await waitFor(() => {
      expect(mockProps.onEditPersonality).toHaveBeenCalledTimes(1);
    });
  });

  it('calls onManageUsers when manage users item is clicked', async () => {
    const user = userEvent.setup();
    renderComponent();

    const trigger = screen.getByRole('button', { name: /more actions/i });
    await user.click(trigger);

    const manageItem = screen.getByText(/manage users/i);
    await user.click(manageItem);

    // Wait for the setTimeout to execute
    await waitFor(() => {
      expect(mockProps.onManageUsers).toHaveBeenCalledTimes(1);
    });
  });

  it('calls onDeleteThread when delete thread item is clicked', async () => {
    const user = userEvent.setup();
    renderComponent();

    const trigger = screen.getByRole('button', { name: /more actions/i });
    await user.click(trigger);

    const deleteItem = screen.getByText(/delete thread/i);
    await user.click(deleteItem);

    // Wait for the setTimeout to execute
    await waitFor(() => {
      expect(mockProps.onDeleteThread).toHaveBeenCalledTimes(1);
    });
  });

  it('closes dropdown after clicking an item', async () => {
    const user = userEvent.setup();
    renderComponent();

    const trigger = screen.getByRole('button', { name: /more actions/i });
    await user.click(trigger);

    // Verify dropdown is open
    expect(screen.getByText(/show system messages/i)).toBeInTheDocument();

    // Click an item
    const toggleItem = screen.getByText(/show system messages/i);
    await user.click(toggleItem);

    // Verify dropdown is closed
    await waitFor(() => {
      expect(screen.queryByText(/show system messages/i)).not.toBeInTheDocument();
    });
  });

  it('applies destructive styling to delete thread item', async () => {
    const user = userEvent.setup();
    renderComponent();

    const trigger = screen.getByRole('button', { name: /more actions/i });
    await user.click(trigger);

    const deleteItem = screen.getByText(/delete thread/i).closest('[role="menuitem"]');
    expect(deleteItem).toHaveClass('text-destructive');
  });

  describe('Permission-based visibility', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('hides edit personality when user cannot manage thread', async () => {
      mockUseThreadPermissions.mockReturnValue({
        canManage: false,
        canManageUsers: true,
        canDelete: true,
        canViewSystemMessages: true,
        shouldShowComponent: true,
      });

      const user = userEvent.setup();
      renderComponent();

      const trigger = screen.getByRole('button', { name: /more actions/i });
      await user.click(trigger);

      expect(screen.getByText(/show system messages/i)).toBeInTheDocument();
      expect(screen.queryByText(/edit personality/i)).not.toBeInTheDocument();
      expect(screen.getByText(/manage users/i)).toBeInTheDocument();
      expect(screen.getByText(/delete thread/i)).toBeInTheDocument();
    });

    it('hides manage users when user cannot manage users', async () => {
      mockUseThreadPermissions.mockReturnValue({
        canManage: true,
        canManageUsers: false,
        canDelete: true,
        canViewSystemMessages: true,
        shouldShowComponent: true,
      });

      const user = userEvent.setup();
      renderComponent();

      const trigger = screen.getByRole('button', { name: /more actions/i });
      await user.click(trigger);

      expect(screen.getByText(/show system messages/i)).toBeInTheDocument();
      expect(screen.getByText(/edit personality/i)).toBeInTheDocument();
      expect(screen.queryByText(/manage users/i)).not.toBeInTheDocument();
      expect(screen.getByText(/delete thread/i)).toBeInTheDocument();
    });

    it('hides delete thread when user cannot delete', async () => {
      mockUseThreadPermissions.mockReturnValue({
        canManage: true,
        canManageUsers: true,
        canDelete: false,
        canViewSystemMessages: true,
        shouldShowComponent: true,
      });

      const user = userEvent.setup();
      renderComponent();

      const trigger = screen.getByRole('button', { name: /more actions/i });
      await user.click(trigger);

      expect(screen.getByText(/show system messages/i)).toBeInTheDocument();
      expect(screen.getByText(/edit personality/i)).toBeInTheDocument();
      expect(screen.getByText(/manage users/i)).toBeInTheDocument();
      expect(screen.queryByText(/delete thread/i)).not.toBeInTheDocument();
    });

    it('hides system messages when user cannot view them', async () => {
      mockUseThreadPermissions.mockReturnValue({
        canManage: true,
        canManageUsers: true,
        canDelete: true,
        canViewSystemMessages: false,
        shouldShowComponent: true,
      });

      const user = userEvent.setup();
      renderComponent();

      const trigger = screen.getByRole('button', { name: /more actions/i });
      await user.click(trigger);

      expect(screen.queryByText(/show system messages/i)).not.toBeInTheDocument();
      expect(screen.getByText(/edit personality/i)).toBeInTheDocument();
      expect(screen.getByText(/manage users/i)).toBeInTheDocument();
      expect(screen.getByText(/delete thread/i)).toBeInTheDocument();
    });

    it('hides entire component when user has no permissions', async () => {
      mockUseThreadPermissions.mockReturnValue({
        canManage: false,
        canManageUsers: false,
        canDelete: false,
        canViewSystemMessages: false,
        shouldShowComponent: false,
      });

      renderComponent();

      expect(screen.queryByRole('button', { name: /more actions/i })).not.toBeInTheDocument();
    });
  });
});
