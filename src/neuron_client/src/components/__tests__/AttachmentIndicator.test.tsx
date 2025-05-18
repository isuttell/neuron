import { render, screen, fireEvent } from "@testing-library/react";
import { AttachmentIndicator } from "../AttachmentIndicator";

describe("AttachmentIndicator", () => {
  const mockOnRemove = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders audio attachment indicator correctly", () => {
    render(<AttachmentIndicator type="audio" onRemove={mockOnRemove} />);

    expect(screen.getByText("Audio recording attached")).toBeInTheDocument();
    expect(screen.getByLabelText("Remove attachment")).toBeInTheDocument();
  });

  it("renders file attachment indicator with filename correctly", () => {
    const fileName = "test-file.pdf";
    render(<AttachmentIndicator type="file" name={fileName} onRemove={mockOnRemove} />);

    expect(screen.getByText(`File attached: ${fileName}`)).toBeInTheDocument();
    expect(screen.getByLabelText("Remove attachment")).toBeInTheDocument();
  });

  it("calls onRemove when remove button is clicked", () => {
    render(<AttachmentIndicator type="audio" onRemove={mockOnRemove} />);

    const removeButton = screen.getByLabelText("Remove attachment");
    fireEvent.click(removeButton);

    expect(mockOnRemove).toHaveBeenCalledTimes(1);
  });
});
