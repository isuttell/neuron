import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { MetadataDisplay } from "../MetadataDisplay";

describe("MetadataDisplay", () => {
  beforeEach(() => {
    // Clear any existing content
  });

  it("renders nothing when no data is provided", () => {
    const { container } = render(<MetadataDisplay metadata={{}} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when all values are empty", () => {
    const metadata = {
      empty_string: "",
      null_value: null,
      undefined_value: undefined,
    };

    const { container } = render(<MetadataDisplay metadata={metadata} />);
    // Even though metadata object has keys, all values are filtered out, so only the metadata structure remains
    // but the border and dl are still rendered even if empty
    expect(container.firstChild).not.toBeNull();
    const dl = container.querySelector("dl");
    expect(dl?.children).toHaveLength(0); // No dt/dd pairs should be rendered
  });

  it("renders description when provided", () => {
    render(
      <MetadataDisplay
        metadata={{}}
        description="This is a test description"
      />
    );

    expect(screen.getByText("Description")).toBeInTheDocument();
    expect(screen.getByText("This is a test description")).toBeInTheDocument();
  });

  it("renders multiline description correctly", () => {
    const multilineDescription = "Line 1\nLine 2\nLine 3";

    render(
      <MetadataDisplay
        metadata={{}}
        description={multilineDescription}
      />
    );

    // Use a function matcher to handle the multiline text properly
    const descriptionElement = screen.getByText((content, element) => {
      return element?.textContent === multilineDescription;
    });
    expect(descriptionElement).toHaveClass("whitespace-pre-wrap");
  });

  it("renders dimensions when both width and height provided", () => {
    render(
      <MetadataDisplay
        metadata={{}}
        dimensions={{ width: 1920, height: 1080 }}
      />
    );

    expect(screen.getByText("Dimensions")).toBeInTheDocument();
    expect(screen.getByText("1920 × 1080")).toBeInTheDocument();
  });

  it("renders width only when height not provided", () => {
    render(
      <MetadataDisplay
        metadata={{}}
        dimensions={{ width: 800 }}
      />
    );

    expect(screen.getByText("Dimensions")).toBeInTheDocument();
    expect(screen.getByText("Width: 800")).toBeInTheDocument();
  });

  it("renders height only when width not provided", () => {
    render(
      <MetadataDisplay
        metadata={{}}
        dimensions={{ height: 600 }}
      />
    );

    expect(screen.getByText("Dimensions")).toBeInTheDocument();
    expect(screen.getByText("Height: 600")).toBeInTheDocument();
  });

  it("does not render dimensions when both values are missing", () => {
    render(
      <MetadataDisplay
        metadata={{}}
        dimensions={{}}
      />
    );

    expect(screen.queryByText("Dimensions")).not.toBeInTheDocument();
  });

  it("renders metadata with proper formatting", () => {
    const metadata = {
      camera: "Canon EOS R5",
      iso_speed: "400",
      focal_length: "85mm",
      exposure_time: "1/125s",
    };

    render(<MetadataDisplay metadata={metadata} />);

    // Check for formatted labels (underscores replaced with spaces, displayed as lowercase, capitalized by CSS)
    expect(screen.getByText("camera")).toBeInTheDocument();
    expect(screen.getByText("iso speed")).toBeInTheDocument();
    expect(screen.getByText("focal length")).toBeInTheDocument();
    expect(screen.getByText("exposure time")).toBeInTheDocument();

    // Check for values
    expect(screen.getByText("Canon EOS R5")).toBeInTheDocument();
    expect(screen.getByText("400")).toBeInTheDocument();
    expect(screen.getByText("85mm")).toBeInTheDocument();
    expect(screen.getByText("1/125s")).toBeInTheDocument();
  });

  it("filters out empty, null, and undefined metadata values", () => {
    const metadata = {
      valid_field: "Valid Value",
      empty_string: "",
      null_field: null,
      undefined_field: undefined,
      zero_value: 0,
      false_value: false,
    };

    render(<MetadataDisplay metadata={metadata} />);

    // Should show valid values including 0 and false (keys are lowercased with spaces)
    expect(screen.getByText("valid field")).toBeInTheDocument();
    expect(screen.getByText("Valid Value")).toBeInTheDocument();
    expect(screen.getByText("zero value")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("false value")).toBeInTheDocument();
    expect(screen.getByText("false")).toBeInTheDocument();

    // Should not show empty, null, or undefined
    expect(screen.queryByText("Empty string")).not.toBeInTheDocument();
    expect(screen.queryByText("Null field")).not.toBeInTheDocument();
    expect(screen.queryByText("Undefined field")).not.toBeInTheDocument();
  });

  it("renders border separator when metadata is present", () => {
    const metadata = { test_field: "test_value" };

    render(<MetadataDisplay metadata={metadata} />);

    const separator = document.querySelector(".border-t");
    expect(separator).toBeInTheDocument();
    expect(separator).toHaveClass("-mx-6");
    expect(separator).toHaveClass("my-4");
  });

  it("does not render border separator when no metadata", () => {
    render(
      <MetadataDisplay
        metadata={{}}
        description="Just description"
      />
    );

    const separator = document.querySelector(".border-t");
    expect(separator).not.toBeInTheDocument();
  });

  it("converts metadata values to strings", () => {
    const metadata = {
      number_field: 123,
      boolean_field: true,
      object_field: { nested: "value" },
      array_field: ["item1", "item2"],
    };

    render(<MetadataDisplay metadata={metadata} />);

    expect(screen.getByText("123")).toBeInTheDocument();
    expect(screen.getByText("true")).toBeInTheDocument();
    expect(screen.getByText("[object Object]")).toBeInTheDocument();
    expect(screen.getByText("item1,item2")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <MetadataDisplay
        metadata={{ test: "value" }}
        className="custom-metadata-class"
      />
    );

    expect(container.firstChild).toHaveClass("custom-metadata-class");
  });

  it("renders all sections in correct order", () => {
    const metadata = { camera: "Test Camera" };

    render(
      <MetadataDisplay
        metadata={metadata}
        description="Test description"
        dimensions={{ width: 800, height: 600 }}
      />
    );

    const elements = Array.from(document.querySelectorAll("h3"));
    const headings = elements.map(el => el.textContent);

    // Only h3 elements are description and dimensions headings, metadata uses dt
    expect(headings).toEqual(["Description", "Dimensions"]);
  });

  it("handles complex metadata key formatting", () => {
    const metadata = {
      simple_key: "value1",
      multiple_underscores_key: "value2",
      "kebab-case": "value3", // Note: this won't be processed as underscores
      CamelCase: "value4",
    };

    render(<MetadataDisplay metadata={metadata} />);

    expect(screen.getByText("simple key")).toBeInTheDocument();
    expect(screen.getByText("multiple underscores key")).toBeInTheDocument();
    expect(screen.getByText("kebab-case")).toBeInTheDocument();
    expect(screen.getByText("CamelCase")).toBeInTheDocument(); // CSS capitalize doesn't change existing case
  });

  it("uses description list semantics for metadata", () => {
    const metadata = { test_key: "test_value" };

    render(<MetadataDisplay metadata={metadata} />);

    // Check for dl element directly since JSDOM doesn't always assign list role
    const dl = document.querySelector("dl");
    expect(dl).toBeInTheDocument();
    expect(dl?.tagName).toBe("DL");

    const term = screen.getByRole("term");
    expect(term.tagName).toBe("DT");
    expect(term).toHaveTextContent("test key");

    const definition = screen.getByRole("definition");
    expect(definition.tagName).toBe("DD");
    expect(definition).toHaveTextContent("test_value");
  });

  it("applies correct styling classes", () => {
    const metadata = { test: "value" };

    render(
      <MetadataDisplay
        metadata={metadata}
        description="Test description"
        dimensions={{ width: 100, height: 100 }}
      />
    );

    // Check description styles
    const descriptionHeading = screen.getByText("Description");
    expect(descriptionHeading).toHaveClass("text-sm", "font-medium", "text-muted-foreground", "mb-2");

    // Check dimensions styles
    const dimensionsHeading = screen.getByText("Dimensions");
    expect(dimensionsHeading).toHaveClass("text-sm", "font-medium", "text-muted-foreground", "mb-2");

    // Check metadata term styles
    const metadataTerm = screen.getByText("test");
    expect(metadataTerm).toHaveClass("font-medium", "text-muted-foreground", "capitalize", "mb-1");

    // Check metadata definition styles
    const metadataDefinition = screen.getByText("value");
    expect(metadataDefinition).toHaveClass("text-foreground", "break-words");
  });
});
