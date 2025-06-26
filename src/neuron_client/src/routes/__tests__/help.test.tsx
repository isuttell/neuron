import { vi } from 'vitest';
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Mock UI components
vi.mock("@/components/ui/sidebar", () => ({
  SidebarTrigger: ({ className }: { className: string }) => (
    <div data-testid="sidebar-trigger" className={className}>
      Sidebar Trigger
    </div>
  ),
}));

vi.mock("@/components/ui/scroll-area", () => ({
  ScrollArea: ({ children, className }: { children: React.ReactNode; className: string }) => (
    <div data-testid="scroll-area" className={className}>
      {children}
    </div>
  ),
}));

// Import component after mocks
import Help from "../help";

describe("Help Route Component", () => {
  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <Help />
      </MemoryRouter>
    );
  };

  describe("UI Rendering", () => {
    it("should render the main layout structure", () => {
      renderComponent();

      // Check main container by class since it doesn't have role="main"
      const container = document.querySelector(".flex.flex-1.p-4.ipad-top-spacing");
      expect(container).toBeInTheDocument();
      expect(container).toHaveClass(
        "flex",
        "flex-1",
        "p-4",
        "ipad-top-spacing",
        "flex-col",
        "flex-nowrap",
        "max-h-screen",
        "overflow-auto"
      );
    });

    it("should render the header with sidebar trigger and title", () => {
      renderComponent();

      // Check sidebar trigger
      const sidebarTrigger = screen.getByTestId("sidebar-trigger");
      expect(sidebarTrigger).toBeInTheDocument();
      expect(sidebarTrigger).toHaveClass("size-10", "mr-2");

      // Check title
      const title = screen.getByRole("heading", { level: 1 });
      expect(title).toBeInTheDocument();
      expect(title).toHaveTextContent("Help");
      expect(title).toHaveClass("text-lg", "lg:text-2xl", "font-bold");
    });

    it("should render the header with proper mobile spacing", () => {
      renderComponent();

      // Find header by class since it doesn't have role="banner"
      const header = document.querySelector(".flex.items-center.justify-between.mb-2.border-b.pb-2.mobile-safe-top");
      expect(header).toBeInTheDocument();
      expect(header).toHaveClass(
        "flex",
        "items-center",
        "justify-between",
        "mb-2",
        "border-b",
        "pb-2",
        "mobile-safe-top"
      );
    });

    it("should render the scroll area", () => {
      renderComponent();

      const scrollArea = screen.getByTestId("scroll-area");
      expect(scrollArea).toBeInTheDocument();
      expect(scrollArea).toHaveClass("flex-1");
    });

    it("should render content with proper max width and centering", () => {
      renderComponent();

      const contentContainer = screen.getByTestId("scroll-area").firstChild;
      expect(contentContainer).toHaveClass("space-y-6", "max-w-2xl", "mx-auto");
    });
  });

  describe("Content Sections", () => {
    it("should render the welcome introduction", () => {
      renderComponent();

      const welcomeText = screen.getByText(/Welcome to Neuron!/);
      expect(welcomeText).toBeInTheDocument();
      expect(welcomeText).toHaveClass("text-muted-foreground", "leading-relaxed");
    });

    it("should render all main section headings", () => {
      renderComponent();

      const expectedHeadings = [
        "Getting Started",
        "How Conversations Work",
        "Adding Context to Conversations",
        "Generated Content & Media",
        "Memory & Persistence",
        "Voice Features",
        "Quick Actions & Shortcuts"
      ];

      expectedHeadings.forEach(heading => {
        const headingElement = screen.getByRole("heading", { level: 2, name: heading });
        expect(headingElement).toBeInTheDocument();
        expect(headingElement).toHaveClass("text-xl", "font-semibold", "mb-3");
      });
    });

    it("should render getting started content", () => {
      renderComponent();

      expect(screen.getByText(/The default personality is/)).toBeInTheDocument();
      expect(screen.getByText(/Neuron/, { selector: "strong" })).toBeInTheDocument();
      expect(screen.getByText(/creates a new thread that's private to you/)).toBeInTheDocument();
    });

    it("should render conversation explanation", () => {
      renderComponent();

      expect(screen.getByText(/Neuron isn't a traditional chat app/)).toBeInTheDocument();
      expect(screen.getByText(/Every time you hit enter, it sends a complete prompt/)).toBeInTheDocument();
    });

    it("should render subsection headings in context section", () => {
      renderComponent();

      const contextSubheadings = ["File Uploads", "Website Fetching"];
      contextSubheadings.forEach(subheading => {
        const subheadingElement = screen.getByRole("heading", { level: 3, name: subheading });
        expect(subheadingElement).toBeInTheDocument();
        expect(subheadingElement).toHaveClass("font-medium", "mb-1");
      });
    });

    it("should render voice features subsections", () => {
      renderComponent();

      const voiceSubheadings = ["Audio Recording", "Text-to-Speech"];
      voiceSubheadings.forEach(subheading => {
        const subheadingElement = screen.getByRole("heading", { level: 3, name: subheading });
        expect(subheadingElement).toBeInTheDocument();
        expect(subheadingElement).toHaveClass("font-medium", "mb-1");
      });
    });

    it("should render quick actions subsections", () => {
      renderComponent();

      const quickActionSubheadings = ["Prompt Menu", "Clickable Prompts"];
      quickActionSubheadings.forEach(subheading => {
        const subheadingElement = screen.getByRole("heading", { level: 3, name: subheading });
        expect(subheadingElement).toBeInTheDocument();
        expect(subheadingElement).toHaveClass("font-medium", "mb-1");
      });
    });

    it("should render the help footer", () => {
      renderComponent();

      const footerText = screen.getByText(/Need more help\? Try asking Neuron directly/);
      expect(footerText).toBeInTheDocument();
      expect(footerText).toHaveClass("text-xs", "text-muted-foreground");
    });

    it("should render memory section content", () => {
      renderComponent();

      expect(screen.getByText(/Personalities can remember information/)).toBeInTheDocument();
      expect(screen.getByText(/remember this for later/)).toBeInTheDocument();
    });

    it("should render media content explanation", () => {
      renderComponent();

      expect(screen.getByText(/When the AI generates content/)).toBeInTheDocument();
      expect(screen.getByText(/dedicated media viewer/)).toBeInTheDocument();
    });
  });

  describe("Layout and Styling", () => {
    it("should have proper section spacing", () => {
      renderComponent();

      // Check for section elements (they don't have role="region" by default)
      const sections = document.querySelectorAll("section");
      expect(sections.length).toBeGreaterThan(0);
    });

    it("should render footer with border separator", () => {
      renderComponent();

      const footerSection = screen.getByText(/Need more help/).closest("section");
      expect(footerSection).toHaveClass("border-t", "pt-4");
    });

    it("should have proper text styling for subsection content", () => {
      renderComponent();

      // Check that subsection paragraphs exist with the right classes
      const subsectionParagraphs = document.querySelectorAll("p.text-muted-foreground.text-sm.leading-relaxed");
      expect(subsectionParagraphs.length).toBeGreaterThan(0);
    });
  });

  describe("Accessibility", () => {
    it("should have proper heading hierarchy", () => {
      renderComponent();

      const h1 = screen.getByRole("heading", { level: 1 });
      const h2s = screen.getAllByRole("heading", { level: 2 });
      const h3s = screen.getAllByRole("heading", { level: 3 });

      expect(h1).toBeInTheDocument();
      expect(h2s.length).toBeGreaterThan(0);
      expect(h3s.length).toBeGreaterThan(0);
    });

    it("should have semantic HTML structure", () => {
      renderComponent();

      // Check for semantic elements by tag name since no ARIA roles are used
      expect(document.querySelector("h1")).toBeInTheDocument();
      expect(document.querySelectorAll("section").length).toBeGreaterThan(0);
    });
  });
});
