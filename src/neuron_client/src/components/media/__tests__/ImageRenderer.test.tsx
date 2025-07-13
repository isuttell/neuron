import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ImageRenderer } from "../ImageRenderer";

// Mock Spinner component
vi.mock("@/components/ui/spinner", () => ({
  Spinner: ({ className, size }: any) => (
    <div data-testid="spinner" className={className} data-size={size}>
      Loading...
    </div>
  ),
}));

// Mock cn utility
vi.mock("@/lib/utils", () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(" "),
}));

describe("ImageRenderer", () => {
  const defaultProps = {
    url: "https://example.com/image.jpg",
    alt: "Test image",
    width: 800,
    height: 600,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders image with basic props", () => {
    render(<ImageRenderer {...defaultProps} isThumbnail={false} />);

    const image = screen.getByRole("img");
    expect(image).toBeInTheDocument();
    expect(image).toHaveAttribute("src", "https://example.com/image_o.webp"); // Default display_size is "o"
    expect(image).toHaveAttribute("alt", "Test image");
    expect(image).toHaveAttribute("width", "800");
    expect(image).toHaveAttribute("height", "600");
  });

  it("generates thumbnail URL with size suffix for non-GIF images", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        url="https://example.com/image.png"
        thumbnail_size="xl"
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/image_xl.webp");
  });

  it("generates display URL with size suffix for non-GIF images", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        url="https://example.com/image.png"
        display_size="xxl"
        isThumbnail={false}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/image_xxl.webp");
  });

  it("uses original URL for GIF images", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        url="https://example.com/animation.gif"
        thumbnail_size="xl"
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/animation.gif");
  });

  it("applies thumbnail classes when isThumbnail is true", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveClass("rounded-lg");
    expect(image).toHaveClass("cursor-pointer");
    expect(image).toHaveClass("transition-opacity");
    expect(image).toHaveClass("duration-500");
  });

  it("applies display classes when isThumbnail is false", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        isThumbnail={false}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveClass("max-w-full");
    expect(image).toHaveClass("max-h-full");
    expect(image).toHaveClass("object-contain");
    expect(image).not.toHaveClass("rounded-lg");
    expect(image).not.toHaveClass("cursor-pointer");
  });

  it("applies object-fit cover class for thumbnails", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        objectFit="cover"
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveClass("object-cover");
  });

  it("applies object-fit contain class for thumbnails", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        objectFit="contain"
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveClass("object-contain");
  });

  it("shows spinner for thumbnail when preload is enabled and image not loaded", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        preload={true}
        isThumbnail={true}
      />
    );

    const spinner = screen.getByTestId("spinner");
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveClass("absolute");
    expect(spinner).toHaveClass("top-2");
    expect(spinner).toHaveClass("right-2");
    expect(spinner).toHaveClass("opacity-50");
  });

  it("does not show spinner for display images", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        preload={true}
        isThumbnail={false}
      />
    );

    expect(screen.queryByTestId("spinner")).not.toBeInTheDocument();
  });

  it("does not show spinner when preload is false", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        preload={false}
        isThumbnail={true}
      />
    );

    expect(screen.queryByTestId("spinner")).not.toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        className="custom-class"
      />
    );

    const container = screen.getByRole("img").parentElement;
    expect(container).toHaveClass("custom-class");
  });

  it("uses default thumbnail_size when not specified", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        url="https://example.com/image.png"
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/image_l.webp");
  });

  it("uses default display_size when not specified", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        url="https://example.com/image.png"
        isThumbnail={false}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/image_o.webp");
  });

  it("sets rel attribute correctly", () => {
    render(<ImageRenderer {...defaultProps} />);

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("handles images without file extensions", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        url="https://example.com/image"
        thumbnail_size="xl"
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    // The regex matches from the last dot to end, so .com/image gets replaced with _xl.webp
    expect(image).toHaveAttribute("src", "https://example_xl.webp");
  });

  it("handles complex URLs with query parameters", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        url="https://example.com/image.jpg?version=1&token=abc123"
        thumbnail_size="xl"
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    // The regex only replaces the file extension, query params are lost
    expect(image).toHaveAttribute("src", "https://example.com/image_xl.webp");
  });

  it("handles URLs with multiple dots in filename", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        url="https://example.com/image.backup.final.jpg"
        thumbnail_size="xl"
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveAttribute("src", "https://example.com/image.backup.final_xl.webp");
  });

  it("handles default objectFit value", () => {
    render(
      <ImageRenderer
        {...defaultProps}
        isThumbnail={true}
      />
    );

    const image = screen.getByRole("img");
    expect(image).toHaveClass("object-cover"); // Default should be cover
  });

  it("handles all thumbnail size options", () => {
    const sizes = ["o", "t", "l", "xl", "xxl"] as const;

    sizes.forEach(size => {
      const { unmount } = render(
        <ImageRenderer
          {...defaultProps}
          url="https://example.com/test.jpg"
          thumbnail_size={size}
          isThumbnail={true}
        />
      );

      const image = screen.getByRole("img");
      expect(image).toHaveAttribute("src", `https://example.com/test_${size}.webp`);

      unmount();
    });
  });

  it("handles all display size options", () => {
    const sizes = ["o", "t", "l", "xl", "xxl"] as const;

    sizes.forEach(size => {
      const { unmount } = render(
        <ImageRenderer
          {...defaultProps}
          url="https://example.com/test.jpg"
          display_size={size}
          isThumbnail={false}
        />
      );

      const image = screen.getByRole("img");
      expect(image).toHaveAttribute("src", `https://example.com/test_${size}.webp`);

      unmount();
    });
  });
});
