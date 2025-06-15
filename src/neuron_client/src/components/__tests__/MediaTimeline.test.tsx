import { vi } from 'vitest';
import { render, screen } from "@testing-library/react";
import MediaTimeline from "../MediaTimeline";
import { useAppSelector } from "@/hooks";
import { MediaItem } from "@/types/media";

// Mock the hooks
vi.mock("@/hooks", () => ({
  useAppSelector: vi.fn(),
}));

// Mock child components to focus on the MediaTimeline logic
vi.mock("@/messages/ImageContent", () => ({
  __esModule: true,
  default: ({ thumbnail_size }: { thumbnail_size: string }) => (
    <div data-testid="image-content" data-thumbnail-size={thumbnail_size} />
  ),
}));

vi.mock("@/messages/SpeechAudioContent", () => ({
  __esModule: true,
  default: () => <div data-testid="speech-audio-content" />,
}));

vi.mock("@/messages/SubtitleContent", () => ({
  SubtitleContent: () => <div data-testid="subtitle-content" />,
}));

vi.mock("@/messages/VideoContent", () => ({
  __esModule: true,
  default: () => <div data-testid="video-content" />,
}));

vi.mock("@/components/TimelineControls", () => ({
  TimelineControls: () => <div data-testid="timeline-controls" />,
}));

const mockedUseAppSelector = useAppSelector as vi.MockedFunction<typeof useAppSelector>;

describe("MediaTimeline", () => {
  const mockThreadId = "thread-123";

  // Sample media items
  const mockMediaItems: MediaItem[] = [
    {
      id: "media-1",
      name: "Test Image 1",
      description: "Test image description",
      url: "https://example.com/image1.jpg",
      media_type: "image",
      user_id: "user-1",
      thread_id: mockThreadId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "media-2",
      name: "Test Audio 1",
      description: "Test audio description",
      url: "https://example.com/audio1.mp3",
      media_type: "audio",
      user_id: "user-1",
      thread_id: mockThreadId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "media-3",
      name: "Test Image 2",
      description: "Another test image",
      url: "https://example.com/image2.png",
      media_type: "image",
      user_id: "user-1",
      thread_id: mockThreadId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(() => null),
        setItem: vi.fn(),
      },
      writable: true,
    });
  });

  it("renders with no media message when no items", () => {
    mockedUseAppSelector.mockReturnValue([]);

    render(<MediaTimeline threadId={mockThreadId} />);

    expect(screen.getByText("No media")).toBeInTheDocument();
  });

  it("renders image content with consistent thumbnail size", () => {
    mockedUseAppSelector.mockReturnValue(mockMediaItems);

    render(<MediaTimeline threadId={mockThreadId} />);

    const imageElements = screen.getAllByTestId("image-content");
    expect(imageElements).toHaveLength(2); // Two image items

    // All should use "l" (large) as consistent size
    imageElements.forEach(element => {
      expect(element).toHaveAttribute("data-thumbnail-size", "l");
    });
  });

  it("filters media items by thread ID", () => {
    const mixedMediaItems = [
      ...mockMediaItems,
      {
        id: "media-other",
        name: "Other Thread Image",
        description: "Image from another thread",
        url: "https://example.com/other.jpg",
        media_type: "image",
        user_id: "user-1",
        thread_id: "other-thread",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    mockedUseAppSelector.mockReturnValue(mixedMediaItems);

    render(<MediaTimeline threadId={mockThreadId} />);

    // Should only render images from the specified thread
    const imageElements = screen.getAllByTestId("image-content");
    expect(imageElements).toHaveLength(2); // Only the two from mockThreadId
  });

  it("renders audio and other media types", () => {
    mockedUseAppSelector.mockReturnValue(mockMediaItems);

    render(<MediaTimeline threadId={mockThreadId} />);

    expect(screen.getByTestId("speech-audio-content")).toBeInTheDocument();
    expect(screen.getAllByTestId("image-content")).toHaveLength(2);
  });

  it("renders timeline controls when audio items are present", () => {
    mockedUseAppSelector.mockReturnValue(mockMediaItems);

    render(<MediaTimeline threadId={mockThreadId} />);

    expect(screen.getByTestId("timeline-controls")).toBeInTheDocument();
  });

  it("does not render timeline controls when no audio items", () => {
    const imageOnlyItems = mockMediaItems.filter(item => item.media_type === "image");
    mockedUseAppSelector.mockReturnValue(imageOnlyItems);

    render(<MediaTimeline threadId={mockThreadId} />);

    expect(screen.queryByTestId("timeline-controls")).not.toBeInTheDocument();
  });
});
