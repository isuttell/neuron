import { render, fireEvent, waitFor } from "@testing-library/react";
import { AudioBarVisualization } from "../AudioBarVisualization";

// Mock AudioContext
const mockDecode = jest.fn();
const mockGetChannelData = jest.fn();
const mockClose = jest.fn();

class MockAudioContext {
  decodeAudioData = mockDecode;
  close = mockClose;
}

global.AudioContext = MockAudioContext as unknown as typeof AudioContext;

// Mock canvas context
const mockFillRect = jest.fn();
const mockGetContext = jest.fn(() => ({
  fillRect: mockFillRect,
  fillStyle: "",
})) as jest.Mock;

// Mock fetch
global.fetch = jest.fn();

// Mock requestAnimationFrame
global.requestAnimationFrame = jest.fn((cb) => {
  cb(0);
  return 1;
});
global.cancelAnimationFrame = jest.fn();

// Mock ResizeObserver
class MockResizeObserver {
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
}
global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

describe("AudioBarVisualization", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    HTMLCanvasElement.prototype.getContext = mockGetContext;

    // Mock canvas properties
    Object.defineProperty(HTMLCanvasElement.prototype, 'clientWidth', {
      configurable: true,
      get: function() { return 100; }
    });
    Object.defineProperty(HTMLCanvasElement.prototype, 'clientHeight', {
      configurable: true,
      get: function() { return 50; }
    });
    Object.defineProperty(HTMLCanvasElement.prototype, 'parentElement', {
      configurable: true,
      get: function() {
        return {
          clientWidth: 100,
          clientHeight: 50
        };
      }
    });

    // Setup default mock responses
    (global.fetch as jest.Mock).mockResolvedValue({
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
    });

    mockDecode.mockResolvedValue({
      getChannelData: mockGetChannelData,
    });

    mockGetChannelData.mockReturnValue(new Float32Array([0.5, -0.5, 0.3, -0.3, 0.1, -0.1]));
  });

  it("renders canvas element", () => {
    const { container } = render(
      <div style={{ width: '100px', height: '50px' }}>
        <AudioBarVisualization src="test.mp3" progress={0} />
      </div>
    );
    const canvas = container.querySelector("canvas");
    expect(canvas).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <AudioBarVisualization src="test.mp3" progress={0} className="custom-class" />
    );
    const canvas = container.querySelector("canvas");
    expect(canvas).toHaveClass("custom-class");
  });

  it("sets background color", () => {
    const { container } = render(
      <AudioBarVisualization src="test.mp3" progress={0} backgroundColor="#ff0000" />
    );
    const canvas = container.querySelector("canvas");
    expect(canvas).toHaveStyle({ backgroundColor: "#ff0000" });
  });

  it("loads audio data on mount", async () => {
    const onLoadingChange = jest.fn();
    render(<AudioBarVisualization src="test.mp3" progress={0} onLoadingChange={onLoadingChange} />);

    // Since the component checks for canvas ref, we'll verify through the loading callback
    expect(onLoadingChange).toHaveBeenCalledWith(true);
  });

  it("calls onLoadingChange callback", async () => {
    const onLoadingChange = jest.fn();
    render(
      <AudioBarVisualization
        src="test.mp3"
        progress={0}
        onLoadingChange={onLoadingChange}
      />
    );

    expect(onLoadingChange).toHaveBeenCalledWith(true);

    await waitFor(() => {
      expect(onLoadingChange).toHaveBeenCalledWith(false);
    });
  });

  it("draws waveform after loading audio", async () => {
    render(<AudioBarVisualization src="test.mp3" progress={50} />);

    await waitFor(() => {
      expect(mockFillRect).toHaveBeenCalled();
    });
  });

  it("handles click for seeking when onSeek is provided", async () => {
    const onSeek = jest.fn();
    const { container } = render(
      <AudioBarVisualization src="test.mp3" progress={0} onSeek={onSeek} />
    );

    const canvas = container.querySelector("canvas")!;

    // Mock getBoundingClientRect
    canvas.getBoundingClientRect = jest.fn(() => ({
      left: 0,
      width: 100,
      right: 100,
      top: 0,
      bottom: 100,
      height: 100,
      x: 0,
      y: 0,
      toJSON: () => {},
    }));

    fireEvent.mouseDown(canvas, { clientX: 50 });

    expect(onSeek).toHaveBeenCalledWith(50);
  });

  it("sets cursor to pointer when onSeek is provided", () => {
    const { container } = render(
      <AudioBarVisualization src="test.mp3" progress={0} onSeek={() => {}} />
    );
    const canvas = container.querySelector("canvas");
    expect(canvas).toHaveStyle({ cursor: "pointer" });
  });

  it("sets cursor to default when onSeek is not provided", () => {
    const { container } = render(
      <AudioBarVisualization src="test.mp3" progress={0} />
    );
    const canvas = container.querySelector("canvas");
    expect(canvas).toHaveStyle({ cursor: "default" });
  });

  it("handles drag for seeking", async () => {
    const onSeek = jest.fn();
    const { container } = render(
      <AudioBarVisualization src="test.mp3" progress={0} onSeek={onSeek} />
    );

    const canvas = container.querySelector("canvas")!;
    canvas.getBoundingClientRect = jest.fn(() => ({
      left: 0,
      width: 100,
      right: 100,
      top: 0,
      bottom: 100,
      height: 100,
      x: 0,
      y: 0,
      toJSON: () => {},
    }));

    // Start drag
    fireEvent.mouseDown(canvas, { clientX: 25 });
    expect(onSeek).toHaveBeenCalledWith(25);

    // Continue drag
    fireEvent.mouseMove(document, { clientX: 75 });
    expect(onSeek).toHaveBeenCalledWith(75);

    // End drag
    fireEvent.mouseUp(document);

    // Should not call onSeek after mouseUp
    onSeek.mockClear();
    fireEvent.mouseMove(document, { clientX: 50 });
    expect(onSeek).not.toHaveBeenCalled();
  });

  it("renders without errors when src changes", () => {
    const { rerender } = render(
      <AudioBarVisualization src="test.mp3" progress={0} />
    );

    expect(() => {
      rerender(<AudioBarVisualization src="test2.mp3" progress={50} />);
    }).not.toThrow();
  });

  it("handles audio loading error", async () => {
    const consoleError = jest.spyOn(console, "error").mockImplementation(() => {});
    const onLoadingChange = jest.fn();

    (global.fetch as jest.Mock).mockRejectedValue(new Error("Network error"));

    render(
      <AudioBarVisualization
        src="error.mp3"
        progress={0}
        onLoadingChange={onLoadingChange}
      />
    );

    await waitFor(() => {
      expect(consoleError).toHaveBeenCalledWith("Audio loading error:", expect.any(Error));
      expect(onLoadingChange).toHaveBeenCalledWith(false);
    });

    consoleError.mockRestore();
  });

  it("updates when progress changes", () => {
    const { rerender } = render(
      <AudioBarVisualization src="test.mp3" progress={0} />
    );

    // Should handle progress changes without errors
    expect(() => {
      rerender(<AudioBarVisualization src="test.mp3" progress={50} />);
      rerender(<AudioBarVisualization src="test.mp3" progress={100} />);
    }).not.toThrow();
  });

  it("responds to resize events", () => {
    render(
      <AudioBarVisualization src="test.mp3" progress={0} />
    );

    // Should handle resize without errors
    expect(() => {
      fireEvent(window, new Event("resize"));
    }).not.toThrow();
  });

  it("cleans up on unmount", () => {
    const { unmount } = render(
      <AudioBarVisualization src="test.mp3" progress={50} onSeek={() => {}} />
    );

    // Component should clean up without errors
    expect(() => unmount()).not.toThrow();
  });

  it("handles different bar widths and gaps", async () => {
    render(
      <AudioBarVisualization
        src="test.mp3"
        progress={0}
        barWidth={4}
        gap={2}
      />
    );

    await waitFor(() => {
      expect(mockFillRect).toHaveBeenCalled();
    });
  });

  it("clamps seek values to 0-100 range", async () => {
    const onSeek = jest.fn();
    const { container } = render(
      <AudioBarVisualization src="test.mp3" progress={0} onSeek={onSeek} />
    );

    const canvas = container.querySelector("canvas")!;
    canvas.getBoundingClientRect = jest.fn(() => ({
      left: 0,
      width: 100,
      right: 100,
      top: 0,
      bottom: 100,
      height: 100,
      x: 0,
      y: 0,
      toJSON: () => {},
    }));

    // Try to seek beyond 100%
    fireEvent.mouseDown(canvas, { clientX: 150 });
    expect(onSeek).toHaveBeenCalledWith(100);

    // Try to seek before 0%
    fireEvent.mouseDown(canvas, { clientX: -50 });
    expect(onSeek).toHaveBeenCalledWith(0);
  });
});
