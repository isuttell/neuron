import { render, screen } from "@testing-library/react";
import MediaTimeline from "../MediaTimeline";
import { useAppSelector } from "@/hooks";
import { MediaItem } from "@/types/media";

// Mock the hooks
jest.mock("@/hooks", () => ({
  useAppSelector: jest.fn(),
}));

// Mock child components to focus on the MediaTimeline logic
jest.mock("@/messages/ImageContent", () => ({
  __esModule: true,
  default: ({ thumbnail_size }: { thumbnail_size: string }) => (
    <div data-testid="image-content" data-thumbnail-size={thumbnail_size} />
  ),
}));

jest.mock("@/messages/SpeechAudioContent", () => ({
  __esModule: true,
  default: () => <div data-testid="speech-audio-content" />,
}));

jest.mock("@/messages/SubtitleContent", () => ({
  SubtitleContent: () => <div data-testid="subtitle-content" />,
}));

jest.mock("@/messages/VideoContent", () => ({
  __esModule: true,
  default: () => <div data-testid="video-content" />,
}));

jest.mock("@/components/TimelineControls", () => ({
  TimelineControls: () => <div data-testid="timeline-controls" />,
}));

const mockedUseAppSelector = useAppSelector as jest.MockedFunction<typeof useAppSelector>;

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
    jest.clearAllMocks();
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn(() => null),
        setItem: jest.fn(),
      },
      writable: true,
    });
  });

  it("renders with no media message when no items", () => {
    mockedUseAppSelector.mockReturnValue([]);

    render(<MediaTimeline threadId={mockThreadId} />);

    expect(screen.getByText("No media")).toBeInTheDocument();
  });

  it("renders image content with default thumbnail size when no widthMode", () => {
    mockedUseAppSelector.mockReturnValue(mockMediaItems);

    render(<MediaTimeline threadId={mockThreadId} />);

    const imageElements = screen.getAllByTestId("image-content");
    expect(imageElements).toHaveLength(2); // Two image items

    // Both should use "l" (large) as default
    imageElements.forEach(element => {
      expect(element).toHaveAttribute("data-thumbnail-size", "l");
    });
  });

  it("uses large thumbnail size for narrow width mode", () => {
    mockedUseAppSelector.mockReturnValue(mockMediaItems);

    render(<MediaTimeline threadId={mockThreadId} widthMode="narrow" />);

    const imageElements = screen.getAllByTestId("image-content");
    expect(imageElements).toHaveLength(2);

    imageElements.forEach(element => {
      expect(element).toHaveAttribute("data-thumbnail-size", "l");
    });
  });

  it("uses extra-large thumbnail size for wide width mode", () => {
    mockedUseAppSelector.mockReturnValue(mockMediaItems);

    render(<MediaTimeline threadId={mockThreadId} widthMode="wide" />);

    const imageElements = screen.getAllByTestId("image-content");
    expect(imageElements).toHaveLength(2);

    imageElements.forEach(element => {
      expect(element).toHaveAttribute("data-thumbnail-size", "xl");
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

    render(<MediaTimeline threadId={mockThreadId} widthMode="wide" />);

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
