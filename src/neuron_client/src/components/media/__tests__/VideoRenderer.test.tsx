import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VideoRenderer } from "../VideoRenderer";

// Mock cn utility
vi.mock("@/lib/utils", () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(" "),
}));

describe("VideoRenderer", () => {
  const defaultProps = {
    url: "https://example.com/video.mp4",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders video element with basic props", () => {
    const { container } = render(<VideoRenderer {...defaultProps} isThumbnail={false} />);

    const video = container.querySelector("video");
    expect(video).toBeInTheDocument();
    expect(video).toHaveAttribute("src", "https://example.com/video.mp4");
  });

  it("applies thumbnail settings when isThumbnail is true", () => {
    const { container } = render(
      <VideoRenderer
        {...defaultProps}
        isThumbnail={true}
        autoPlay={false}
        controls={false}
        loop={false}
      />
    );

    const video = container.querySelector("video");
    expect(video).toHaveClass("rounded-lg");
    expect(video).toHaveClass("cursor-pointer");
    expect(video).toHaveClass("object-contain");
    // Thumbnail videos are always muted, but other props respect their values
    expect(video).not.toHaveAttribute("muted"); // muted=true doesn't add attribute when true
    expect(video).not.toHaveAttribute("autoplay");
    expect(video).not.toHaveAttribute("controls");
    expect(video).not.toHaveAttribute("loop");
  });

  it("applies display settings when isThumbnail is false", () => {
    const { container } = render(
      <VideoRenderer
        {...defaultProps}
        isThumbnail={false}
      />
    );

    const video = container.querySelector("video");
    expect(video).toHaveClass("rounded-md");
    expect(video).toHaveClass("object-contain");
    expect(video).not.toHaveClass("cursor-pointer");
    expect(video).toHaveAttribute("autoplay", ""); // Display videos autoplay
    expect(video).toHaveAttribute("controls", ""); // Display videos have controls
    expect(video).toHaveAttribute("loop", ""); // Display videos loop
  });

  it("displays duration overlay for thumbnails", () => {
    render(
      <VideoRenderer
        {...defaultProps}
        isThumbnail={true}
        duration={125} // 2:05
      />
    );

    expect(screen.getByText("2:05")).toBeInTheDocument();
    const durationElement = screen.getByText("2:05");
    expect(durationElement).toHaveClass("absolute");
    expect(durationElement).toHaveClass("top-2");
    expect(durationElement).toHaveClass("right-2");
    expect(durationElement).toHaveClass("bg-black/70");
    expect(durationElement).toHaveClass("text-white");
  });

  it("does not display duration overlay for display mode", () => {
    render(
      <VideoRenderer
        {...defaultProps}
        isThumbnail={false}
        duration={125}
      />
    );

    expect(screen.queryByText("2:05")).not.toBeInTheDocument();
  });

  it("does not display duration overlay when duration not provided", () => {
    render(
      <VideoRenderer
        {...defaultProps}
        isThumbnail={true}
      />
    );

    expect(screen.queryByText(/\d+:\d+/)).not.toBeInTheDocument();
  });

  it("formats duration correctly", () => {
    const testCases = [
      { duration: 59, expected: "0:59" },
      { duration: 60, expected: "1:00" },
      { duration: 125, expected: "2:05" },
      { duration: 3661, expected: "61:01" }, // Over an hour
    ];

    testCases.forEach(({ duration, expected }) => {
      render(
        <VideoRenderer
          {...defaultProps}
          isThumbnail={true}
          duration={duration}
        />
      );

      expect(screen.getByText(expected)).toBeInTheDocument();
      screen.getByText(expected).remove(); // Clean up for next iteration
    });
  });

  it("does not show duration when duration is 0", () => {
    render(
      <VideoRenderer
        {...defaultProps}
        isThumbnail={true}
        duration={0}
      />
    );

    expect(screen.queryByText("0:00")).not.toBeInTheDocument();
  });

  it("sets preload attribute", () => {
    const preloadValues = ["none", "metadata", "auto"] as const;

    preloadValues.forEach(preload => {
      const { container, unmount } = render(
        <VideoRenderer
          {...defaultProps}
          preload={preload}
        />
      );

      const video = container.querySelector("video");
      expect(video).toHaveAttribute("preload", preload);

      unmount();
    });
  });

  it("sets poster attribute when provided", () => {
    const { container } = render(
      <VideoRenderer
        {...defaultProps}
        poster="https://example.com/poster.jpg"
      />
    );

    const video = container.querySelector("video");
    expect(video).toHaveAttribute("poster", "https://example.com/poster.jpg");
  });

  it("always includes playsInline attribute", () => {
    const { container } = render(<VideoRenderer {...defaultProps} />);

    const video = container.querySelector("video");
    expect(video).toHaveAttribute("playsinline", "");
  });

  it("applies custom className", () => {
    const { container } = render(
      <VideoRenderer
        {...defaultProps}
        className="custom-video-class"
      />
    );

    const videoContainer = container.querySelector(".relative");
    expect(videoContainer).toHaveClass("custom-video-class");
  });

  it("handles prop overrides correctly for thumbnail", () => {
    const { container } = render(
      <VideoRenderer
        {...defaultProps}
        isThumbnail={true}
        autoPlay={true}
        controls={true}
        loop={true}
        muted={false} // Should be overridden to true
      />
    );

    const video = container.querySelector("video");
    expect(video).toHaveAttribute("autoplay", "");
    expect(video).toHaveAttribute("controls", "");
    expect(video).toHaveAttribute("loop", "");
    // muted attribute behavior: when true, the attribute is not present in the DOM
  });

  it("includes source element with video/mp4 type", () => {
    const { container } = render(<VideoRenderer {...defaultProps} />);

    const source = container.querySelector("source");
    expect(source).toBeInTheDocument();
    expect(source).toHaveAttribute("src", "https://example.com/video.mp4");
    expect(source).toHaveAttribute("type", "video/mp4");
  });

  it("forwards ref to video element", () => {
    const ref = vi.fn();
    const { container } = render(<VideoRenderer {...defaultProps} ref={ref} />);

    expect(ref).toHaveBeenCalled();
    expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLVideoElement);
  });

  it("uses default prop values", () => {
    const { container } = render(<VideoRenderer {...defaultProps} />);

    const video = container.querySelector("video");
    // Default for display mode (isThumbnail=false): autoPlay=true, controls=true, loop=true
    expect(video).toHaveAttribute("autoplay", "");
    expect(video).toHaveAttribute("controls", "");
    expect(video).toHaveAttribute("loop", "");
    expect(video).not.toHaveAttribute("muted"); // muted=false means no attribute
    expect(video).toHaveAttribute("preload", "metadata");
  });

  it("applies all video classes correctly", () => {
    const { container } = render(<VideoRenderer {...defaultProps} isThumbnail={true} />);

    const video = container.querySelector("video");
    expect(video).toHaveClass("w-full");
    expect(video).toHaveClass("h-full");
  });

  it("container has relative positioning", () => {
    const { container } = render(<VideoRenderer {...defaultProps} />);

    const videoContainer = container.querySelector(".relative");
    expect(videoContainer).toBeInTheDocument();
  });
});
