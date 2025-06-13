import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PersonalitySearch from "../PersonalitySearch";

describe("PersonalitySearch", () => {
  const mockOnSearch = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders search input with default placeholder", () => {
    render(<PersonalitySearch onSearch={mockOnSearch} />);

    expect(
      screen.getByPlaceholderText("Search personalities...")
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("renders search input with custom placeholder", () => {
    render(
      <PersonalitySearch
        onSearch={mockOnSearch}
        placeholder="Custom placeholder"
      />
    );

    expect(screen.getByPlaceholderText("Custom placeholder")).toBeInTheDocument();
  });

  it("displays search icon", () => {
    render(<PersonalitySearch onSearch={mockOnSearch} />);

    // The search icon should be present
    const searchIcon = document.querySelector("svg");
    expect(searchIcon).toBeInTheDocument();
  });

  it("calls onSearch when typing in input", async () => {
    render(<PersonalitySearch onSearch={mockOnSearch} debounceMs={50} />);

    const input = screen.getByPlaceholderText("Search personalities...");
    await userEvent.type(input, "test");

    // Wait for debounce
    await waitFor(
      () => {
        expect(mockOnSearch).toHaveBeenCalledWith("test");
      },
      { timeout: 200 }
    );
  });

  it("debounces search calls", async () => {
    render(<PersonalitySearch onSearch={mockOnSearch} debounceMs={100} />);

    const input = screen.getByPlaceholderText("Search personalities...");

    // Type quickly
    await userEvent.type(input, "a");
    await userEvent.type(input, "b");
    await userEvent.type(input, "c");

    // Should not have called onSearch yet
    expect(mockOnSearch).not.toHaveBeenCalled();

    // Wait for debounce
    await waitFor(
      () => {
        expect(mockOnSearch).toHaveBeenCalledWith("abc");
      },
      { timeout: 200 }
    );

    // Should only be called once after debounce
    expect(mockOnSearch).toHaveBeenCalledTimes(1);
  });

  it("shows clear button when input has text", async () => {
    render(<PersonalitySearch onSearch={mockOnSearch} />);

    const input = screen.getByPlaceholderText("Search personalities...");

    // Initially no clear button
    expect(screen.queryByRole("button")).not.toBeInTheDocument();

    // Type some text
    await userEvent.type(input, "test");

    // Clear button should appear
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("clears input when clear button is clicked", async () => {
    render(<PersonalitySearch onSearch={mockOnSearch} debounceMs={50} />);

    const input = screen.getByPlaceholderText("Search personalities...");

    // Type some text
    await userEvent.type(input, "test");
    expect(input).toHaveValue("test");

    // Click clear button
    const clearButton = screen.getByRole("button");
    fireEvent.click(clearButton);

    // Input should be cleared
    expect(input).toHaveValue("");

    // Should call onSearch with empty string
    await waitFor(
      () => {
        expect(mockOnSearch).toHaveBeenCalledWith("");
      },
      { timeout: 200 }
    );
  });

  it("calls onSearch with empty string when input is cleared", async () => {
    render(<PersonalitySearch onSearch={mockOnSearch} debounceMs={50} />);

    const input = screen.getByPlaceholderText("Search personalities...");

    // Type and then clear
    await userEvent.type(input, "test");
    await userEvent.clear(input);

    // Wait for debounce
    await waitFor(
      () => {
        expect(mockOnSearch).toHaveBeenCalledWith("");
      },
      { timeout: 200 }
    );
  });

  it("uses default debounce time when not specified", async () => {
    render(<PersonalitySearch onSearch={mockOnSearch} />);

    const input = screen.getByPlaceholderText("Search personalities...");
    await userEvent.type(input, "test");

    // Wait for default debounce (100ms)
    await waitFor(
      () => {
        expect(mockOnSearch).toHaveBeenCalledWith("test");
      },
      { timeout: 200 }
    );
  });
});
