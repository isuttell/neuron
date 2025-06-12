import { vi } from 'vitest';
import { render } from "@testing-library/react";
import { ThreadsUpdating } from "../ThreadsUpdating";
import { useAppSelector } from "@/hooks";
import { Thread } from "@/types/thread";

// Mock the Redux hooks
vi.mock("@/hooks", () => ({
  useAppSelector: vi.fn(),
}));

// Type assertion for the mocked hook
const mockedUseAppSelector = useAppSelector as vi.MockedFunction<typeof useAppSelector>;

describe("ThreadsUpdating", () => {
  // Mock data for different test scenarios
  const mockThreadsIdle: Thread[] = [
    {
      id: "1",
      name: "Thread 1",
      context: "",
      memory: "",
      personality_id: "p1",
      status: "idle",
      message_count: 5,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "2",
      name: "Thread 2",
      context: "",
      memory: "",
      personality_id: "p2",
      status: "idle",
      message_count: 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  const createActiveThread = (): Thread => ({
    id: "3",
    name: "Active Thread",
    context: "",
    memory: "",
    personality_id: "p3",
    status: "active",
    message_count: 2,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });

  const createOldActiveThread = (): Thread => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000);
    return {
      id: "4",
      name: "Old Active Thread",
      context: "",
      memory: "",
      personality_id: "p4",
      status: "active",
      message_count: 1,
      created_at: twoHoursAgo.toISOString(),
      updated_at: twoHoursAgo.toISOString(),
    };
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render a spinner when there are active threads updated within the last hour", () => {
    // Mock the selector to return active + idle threads
    const mockThreads = [...mockThreadsIdle, createActiveThread()];
    mockedUseAppSelector.mockReturnValue(mockThreads);

    // Render the component
    const { container } = render(<ThreadsUpdating />);

    // Verify the spinner is rendered
    const spinner = container.querySelector("svg");
    expect(spinner).toBeInTheDocument();
    expect(spinner?.tagName.toLowerCase()).toBe("svg");
    expect(spinner).toHaveClass("animate-spin");
    expect(spinner).toHaveClass("size-4");
  });

  it("should not render anything when there are only idle threads", () => {
    // Mock the selector to return only idle threads
    mockedUseAppSelector.mockReturnValue(mockThreadsIdle);

    // Render the component
    const { container } = render(<ThreadsUpdating />);

    // Verify nothing is rendered
    expect(container).toBeEmptyDOMElement();
  });

  it("should not render anything when active threads are older than an hour", () => {
    // Mock the selector to return idle + old active threads
    const mockThreads = [...mockThreadsIdle, createOldActiveThread()];
    mockedUseAppSelector.mockReturnValue(mockThreads);

    // Render the component
    const { container } = render(<ThreadsUpdating />);

    // Verify nothing is rendered
    expect(container).toBeEmptyDOMElement();
  });

  it("should update when thread status changes", () => {
    // Start with idle threads
    mockedUseAppSelector.mockReturnValue(mockThreadsIdle);
    const { rerender, container } = render(<ThreadsUpdating />);

    // Verify nothing is rendered initially
    expect(container).toBeEmptyDOMElement();

    // Update to include an active thread
    const mockThreadsWithActive = [...mockThreadsIdle, createActiveThread()];
    mockedUseAppSelector.mockReturnValue(mockThreadsWithActive);
    rerender(<ThreadsUpdating />);

    // Verify the spinner appears
    const spinner = container.querySelector("svg");
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveClass("animate-spin");

    // Update back to only idle threads
    mockedUseAppSelector.mockReturnValue(mockThreadsIdle);
    rerender(<ThreadsUpdating />);

    // Verify the spinner disappears
    expect(container).toBeEmptyDOMElement();
  });
});
