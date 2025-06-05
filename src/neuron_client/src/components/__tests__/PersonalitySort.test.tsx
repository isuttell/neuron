import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

// Test component to isolate personality sorting logic
interface TestPersonality {
  id: string;
  name?: string | null;
}

const PersonalitySelector = ({ personalities }: { personalities: (TestPersonality | null | undefined)[] }) => {
  const sortedPersonalities = personalities
    .filter(p => p && p.name) // Filter out null/undefined personalities
    .slice()
    .sort((a, b) => {
      // Add null checks for name property
      const nameA = a?.name || "";
      const nameB = b?.name || "";
      return nameA.localeCompare(nameB);
    });

  return (
    <div>
      {sortedPersonalities.map((personality) => (
        <div key={personality.id} data-testid="personality-option">
          {personality.name || "Unnamed"}
        </div>
      ))}
    </div>
  );
};

describe("Personality Sorting", () => {
  it("sorts personalities with valid names correctly", () => {
    const personalities = [
      { id: "1", name: "Zebra" },
      { id: "2", name: "Alpha" },
      { id: "3", name: "Beta" },
    ];

    render(<PersonalitySelector personalities={personalities} />);

    const options = screen.getAllByTestId("personality-option");
    expect(options).toHaveLength(3);
    expect(options[0]).toHaveTextContent("Alpha");
    expect(options[1]).toHaveTextContent("Beta");
    expect(options[2]).toHaveTextContent("Zebra");
  });

  it("filters out personalities with null or undefined names", () => {
    const personalities = [
      { id: "1", name: "Valid Name" },
      { id: "2", name: null },
      { id: "3", name: undefined },
      { id: "4", name: "" },
    ];

    render(<PersonalitySelector personalities={personalities} />);

    const options = screen.getAllByTestId("personality-option");
    // Only personality with valid name should be shown (null/undefined filtered out)
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveTextContent("Valid Name");
  });

  it("handles empty personality list", () => {
    render(<PersonalitySelector personalities={[]} />);

    const options = screen.queryAllByTestId("personality-option");
    expect(options).toHaveLength(0);
  });

  it("handles mixed valid and invalid personalities", () => {
    const personalities = [
      { id: "1", name: "Charlie" },
      { id: "2", name: null },
      { id: "3", name: "Alice" },
      { id: "4", name: undefined },
      { id: "5", name: "Bob" },
    ];

    render(<PersonalitySelector personalities={personalities} />);

    const options = screen.getAllByTestId("personality-option");
    // Only valid personalities should be shown, sorted alphabetically
    expect(options).toHaveLength(3);
    expect(options[0]).toHaveTextContent("Alice");
    expect(options[1]).toHaveTextContent("Bob");
    expect(options[2]).toHaveTextContent("Charlie");
  });

  it("does not crash when personality object is null", () => {
    const personalities: (TestPersonality | null | undefined)[] = [
      { id: "1", name: "Valid" },
      null,
      undefined,
    ];

    // Should not throw error
    expect(() => render(<PersonalitySelector personalities={personalities} />)).not.toThrow();

    const options = screen.getAllByTestId("personality-option");
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveTextContent("Valid");
  });

  it("does not crash with localeCompare on undefined values", () => {
    const personalities = [
      { id: "1", name: "Beta" },
      { id: "2", name: undefined },
      { id: "3", name: "Alpha" },
    ];

    // The filter should remove undefined names before sorting
    expect(() => render(<PersonalitySelector personalities={personalities} />)).not.toThrow();

    const options = screen.getAllByTestId("personality-option");
    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent("Alpha");
    expect(options[1]).toHaveTextContent("Beta");
  });
});
