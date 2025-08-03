import { vi } from 'vitest';
import { render, screen } from "@testing-library/react";
import MediaTimeline from "../MediaTimeline";
import { MediaItem } from "@/types/media";

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

describe("MediaTimeline", () => {

  // Sample media items
  const mockMediaItems: MediaItem[] = [
    {
      id: "media-1",
      name: "Test Image 1",
      description: "Test image description",
      url: "https://example.com/image1.jpg",
      media_type: "image",
      user_id: "user-1",
      created_at: "2024-01-01T10:00:00Z",
      updated_at: "2024-01-01T10:00:00Z",
    },
    {
      id: "media-2",
      name: "Test Audio 1",
      description: "Test audio description",
      url: "https://example.com/audio1.mp3",
      media_type: "audio",
      user_id: "user-1",
      created_at: "2024-01-01T10:00:00Z",
      updated_at: "2024-01-01T10:00:00Z",
    },
    {
      id: "media-3",
      name: "Test Image 2",
      description: "Another test image",
      url: "https://example.com/image2.png",
      media_type: "image",
      user_id: "user-1",
      created_at: "2024-01-01T10:00:00Z",
      updated_at: "2024-01-01T10:00:00Z",
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
    render(<MediaTimeline mediaItems={[]} contextId="test-context" />);

    expect(screen.getByText("No media")).toBeInTheDocument();
  });

  it("renders image content with consistent thumbnail size", () => {
    render(<MediaTimeline mediaItems={mockMediaItems} contextId="test-context" />);

    const imageElements = screen.getAllByTestId("image-content");
    expect(imageElements).toHaveLength(2); // Two image items

    // All should use "l" (large) as consistent size
    imageElements.forEach(element => {
      expect(element).toHaveAttribute("data-thumbnail-size", "l");
    });
  });

  it("renders all passed media items", () => {
    const mixedMediaItems = [
      ...mockMediaItems,
      {
        id: "media-other",
        name: "Additional Image",
        description: "Another image item",
        url: "https://example.com/other.jpg",
        media_type: "image",
        user_id: "user-1",
        created_at: "2024-01-01T13:00:00Z",
        updated_at: "2024-01-01T13:00:00Z",
      },
    ];

    render(<MediaTimeline mediaItems={mixedMediaItems} contextId="test-context" />);

    // Should render all passed image items
    const imageElements = screen.getAllByTestId("image-content");
    expect(imageElements).toHaveLength(3); // All three image items
  });

  it("renders audio and other media types", () => {
    render(<MediaTimeline mediaItems={mockMediaItems} contextId="test-context" />);

    expect(screen.getByTestId("speech-audio-content")).toBeInTheDocument();
    expect(screen.getAllByTestId("image-content")).toHaveLength(2);
  });

  it("renders timeline controls when audio items are present", () => {
    render(<MediaTimeline mediaItems={mockMediaItems} contextId="test-context" />);

    expect(screen.getByTestId("timeline-controls")).toBeInTheDocument();
  });

  it("does not render timeline controls when no audio items", () => {
    const imageOnlyItems = mockMediaItems.filter(item => item.media_type === "image");

    render(<MediaTimeline mediaItems={imageOnlyItems} contextId="test-context" />);

    expect(screen.queryByTestId("timeline-controls")).not.toBeInTheDocument();
  });
});
