import { render } from "@testing-library/react";
import { ThreadTitleUpdater } from "../ThreadTitleUpdater";
import { useAppSelector } from "@/hooks";
import { Thread } from "@/types/thread";

// Mock the Redux hooks
jest.mock("@/hooks", () => ({
  useAppSelector: jest.fn(),
}));

// Type assertion for the mocked hook
const mockedUseAppSelector = useAppSelector as jest.MockedFunction<typeof useAppSelector>;

describe("ThreadTitleUpdater", () => {
  // Save the original document.title so we can restore it after tests
  const originalTitle = document.title;

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
    jest.clearAllMocks();
    document.title = originalTitle;
  });

  afterAll(() => {
    document.title = originalTitle;
  });

  it("should not change the title when there are only idle threads", () => {
    // Mock the selector to return idle threads
    mockedUseAppSelector.mockReturnValue(mockThreadsIdle);

    // Render the component
    render(<ThreadTitleUpdater />);

    // Verify the title is set to default
    expect(document.title).toBe("Neuron");
  });

  it("should change the title when there is an active thread updated in the last hour", () => {
    // Mock the selector to return active + idle threads
    const mockThreads = [...mockThreadsIdle, createActiveThread()];
    mockedUseAppSelector.mockReturnValue(mockThreads);

    // Render the component
    render(<ThreadTitleUpdater />);

    // Verify the title includes the loading indicator
    expect(document.title).toBe("🔄 Neuron");
  });

  it("should not change the title when active threads are older than an hour", () => {
    // Mock the selector to return idle + old active threads
    const mockThreads = [...mockThreadsIdle, createOldActiveThread()];
    mockedUseAppSelector.mockReturnValue(mockThreads);

    // Render the component
    render(<ThreadTitleUpdater />);

    // Verify the title is set to default
    expect(document.title).toBe("Neuron");
  });

  it("should reset the title on unmount", () => {
    // Mock the selector to return active threads
    const mockThreads = [...mockThreadsIdle, createActiveThread()];
    mockedUseAppSelector.mockReturnValue(mockThreads);

    // Render the component
    const { unmount } = render(<ThreadTitleUpdater />);

    // Verify the title is set with loading indicator
    expect(document.title).toBe("🔄 Neuron");

    // Unmount the component
    unmount();

    // Verify the title is reset
    expect(document.title).toBe("Neuron");
  });

  it("should update the title when threads prop changes", () => {
    // Initially render with idle threads
    mockedUseAppSelector.mockReturnValue(mockThreadsIdle);
    const { rerender } = render(<ThreadTitleUpdater />);
    expect(document.title).toBe("Neuron");

    // Update to include an active thread
    const mockThreadsWithActive = [...mockThreadsIdle, createActiveThread()];
    mockedUseAppSelector.mockReturnValue(mockThreadsWithActive);
    rerender(<ThreadTitleUpdater />);

    // Verify the title is updated
    expect(document.title).toBe("🔄 Neuron");

    // Update back to only idle threads
    mockedUseAppSelector.mockReturnValue(mockThreadsIdle);
    rerender(<ThreadTitleUpdater />);

    // Verify the title is reset
    expect(document.title).toBe("Neuron");
  });
});
