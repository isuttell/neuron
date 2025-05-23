import { render, screen } from "@testing-library/react";
import FuzzyTimeAgo from "../FuzzyTimeAgo";

// Mock Date.now directly instead of using global
const originalDateNow = Date.now;

describe("FuzzyTimeAgo", () => {
  const NOW = 1621000000000; // Fixed timestamp for tests: 2021-05-14T16:13:20.000Z

  beforeEach(() => {
    // Mock Date.now() to return our fixed timestamp
    Date.now = jest.fn(() => NOW);
  });

  afterEach(() => {
    // Restore the original Date.now implementation
    Date.now = originalDateNow;
  });

  it("renders 'just now' for timestamps less than a minute ago", () => {
    // 30 seconds ago
    const timestamp = NOW - 30 * 1000;
    render(<FuzzyTimeAgo timestamp={timestamp} />);

    expect(screen.getByText("just now")).toBeInTheDocument();
  });

  it("formats minutes correctly", () => {
    // 5 minutes ago
    const timestamp = NOW - 5 * 60 * 1000;
    render(<FuzzyTimeAgo timestamp={timestamp} />);

    expect(screen.getByText("5m")).toBeInTheDocument();
  });

  it("formats hours correctly", () => {
    // 3 hours ago
    const timestamp = NOW - 3 * 60 * 60 * 1000;
    render(<FuzzyTimeAgo timestamp={timestamp} />);

    expect(screen.getByText("3h")).toBeInTheDocument();
  });

  it("formats days correctly", () => {
    // 4 days ago
    const timestamp = NOW - 4 * 24 * 60 * 60 * 1000;
    render(<FuzzyTimeAgo timestamp={timestamp} />);

    expect(screen.getByText("4d")).toBeInTheDocument();
  });

  it("formats months correctly", () => {
    // 2 months ago
    const timestamp = NOW - 2 * 30 * 24 * 60 * 60 * 1000;
    render(<FuzzyTimeAgo timestamp={timestamp} />);

    expect(screen.getByText("2mo")).toBeInTheDocument();
  });

  it("formats years correctly", () => {
    // 3 years ago
    const timestamp = NOW - 3 * 365 * 24 * 60 * 60 * 1000;
    render(<FuzzyTimeAgo timestamp={timestamp} />);

    expect(screen.getByText("3y")).toBeInTheDocument();
  });

  it("adds 'ago' suffix when ago prop is true", () => {
    // 5 minutes ago
    const timestamp = NOW - 5 * 60 * 1000;
    render(<FuzzyTimeAgo timestamp={timestamp} ago={true} />);

    expect(screen.getByText("5m ago")).toBeInTheDocument();
  });

  it("applies the className prop correctly", () => {
    const timestamp = NOW - 5 * 60 * 1000;
    const { container } = render(<FuzzyTimeAgo timestamp={timestamp} className="custom-class" />);

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("handles string timestamp inputs", () => {
    // Create a date string 3 hours before NOW
    const date = new Date(NOW - 3 * 60 * 60 * 1000);
    const dateString = date.toISOString();

    render(<FuzzyTimeAgo timestamp={dateString} />);

    expect(screen.getByText("3h")).toBeInTheDocument();
  });
});
