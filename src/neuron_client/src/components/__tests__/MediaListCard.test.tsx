import { vi } from 'vitest';
import { render, screen, fireEvent } from "@testing-library/react";
import MediaListCard from "../MediaListCard";
import { useAppSelector } from "@/hooks";
import { useNavigate } from "react-router-dom";
import { MediaList } from "@/slices/mediaListsSlice";
import { MediaItem } from "@/types/media";

// Mock the hooks
vi.mock("@/hooks", () => ({
  useAppSelector: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: vi.fn(),
}));

// Mock MediaTimeline component since we don't need to test its implementation
vi.mock("@/components/MediaTimeline", () => ({
  __esModule: true,
  default: () => <div data-testid="media-timeline" />,
}));

// Type assertion for the mocked hooks
const mockedUseAppSelector = useAppSelector as vi.MockedFunction<typeof useAppSelector>;
const mockedUseNavigate = useNavigate as vi.MockedFunction<typeof useNavigate>;

describe("MediaListCard", () => {
  // Sample media list data
  const mockMediaList: MediaList = {
    id: "list-1",
    name: "Test Media List",
    description: "This is a test media list",
    tags: ["test", "sample"],
    visibility: "private",
    shared_with: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  // Sample media items
  const mockMediaItems: MediaItem[] = [
    {
      id: "media-1",
      name: "Test Media 1",
      description: "Test description 1",
      url: "https://example.com/media1",
      media_type: "audio",
      user_id: "user-1",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "media-2",
      name: "Test Media 2",
      description: "Test description 2",
      url: "https://example.com/media2",
      media_type: "video",
      user_id: "user-1",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  // MediaListItems would connect media items to lists in a real app
  // We don't need to use them directly in our tests because we're mocking the selector

  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock the navigate function
    mockedUseNavigate.mockReturnValue(mockNavigate);

    // Mock the selector to return media items for the list
    mockedUseAppSelector.mockImplementation(() => {
      // This simulates what happens inside the component
      // when it calls useAppSelector with a function
      return mockMediaItems;
    });
  });

  it("renders the media list with correct title and description", () => {
    render(<MediaListCard list={mockMediaList} />);

    expect(screen.getByText("Test Media List")).toBeInTheDocument();
    expect(screen.getByText("This is a test media list")).toBeInTheDocument();
  });

  it("displays the visibility badge with the correct variant", () => {
    render(<MediaListCard list={mockMediaList} />);

    const badge = screen.getByText("private");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("capitalize");
  });

  it("displays the media item count badge", () => {
    render(<MediaListCard list={mockMediaList} />);

    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("displays shared badge when list is shared with others", () => {
    const sharedList = {
      ...mockMediaList,
      shared_with: ["user1", "user2"],
    };

    render(<MediaListCard list={sharedList} />);

    expect(screen.getByText("Shared with 2")).toBeInTheDocument();
  });

  it("does not display shared badge when list is not shared", () => {
    render(<MediaListCard list={mockMediaList} />);

    expect(screen.queryByText(/Shared with/)).not.toBeInTheDocument();
  });

  it("renders the share button when not in shared view", () => {
    render(<MediaListCard list={mockMediaList} />);

    const shareButton = screen.getByRole("button", { name: /Share/i });
    expect(shareButton).toBeInTheDocument();
  });

  it("does not render the share button when in shared view", () => {
    render(<MediaListCard list={mockMediaList} isSharedView={true} />);

    expect(screen.queryByRole("button", { name: /Share/i })).not.toBeInTheDocument();
  });

  it("navigates to correct share URL when share button is clicked", () => {
    render(<MediaListCard list={mockMediaList} />);

    const shareButton = screen.getByRole("button", { name: /Share/i });
    fireEvent.click(shareButton);

    expect(mockNavigate).toHaveBeenCalledWith("/share/list-1");
  });

  it("renders a MediaTimeline component", () => {
    render(<MediaListCard list={mockMediaList} />);

    expect(screen.getByTestId("media-timeline")).toBeInTheDocument();
  });

  it("handles public visibility correctly", () => {
    const publicList = {
      ...mockMediaList,
      visibility: "public",
    };

    render(<MediaListCard list={publicList} />);

    const badge = screen.getByText("public");
    expect(badge).toBeInTheDocument();
    // Should not have outline variant for public lists
    expect(badge).not.toHaveClass("outline");
  });

  it("handles zero media items correctly", () => {
    // Mock to return empty array
    mockedUseAppSelector.mockReturnValue([]);

    render(<MediaListCard list={mockMediaList} />);

    expect(screen.getByText("0")).toBeInTheDocument();
  });
});
