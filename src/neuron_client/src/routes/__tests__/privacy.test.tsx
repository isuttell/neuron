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
import Privacy from "../privacy";

describe("Privacy Route Component", () => {
  const renderComponent = () => {
    return render(
      <MemoryRouter>
        <Privacy />
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
      expect(title).toHaveTextContent("Privacy");
      expect(title).toHaveClass("text-lg", "lg:text-2xl", "font-bold");
    });

    it("should render the header with proper mobile spacing", () => {
      renderComponent();

      // Find header by class since it doesn't have role="banner"
      const header = document.querySelector(".flex.items-center.justify-between.mb-6.border-b.pb-4.mobile-safe-top");
      expect(header).toBeInTheDocument();
      expect(header).toHaveClass(
        "flex",
        "items-center",
        "justify-between",
        "mb-6",
        "border-b",
        "pb-4",
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
    it("should render the introduction", () => {
      renderComponent();

      const introText = screen.getByText(/Neuron is designed with privacy and data control in mind/);
      expect(introText).toBeInTheDocument();
      expect(introText).toHaveClass("text-muted-foreground", "leading-relaxed");
    });

    it("should render all main section headings", () => {
      renderComponent();

      const expectedHeadings = [
        "System Administration",
        "Where Your Data Lives",
        "How Data Sharing Works",
        "Cloud Service Usage",
        "Data Control Philosophy",
        "Future Plans",
        "Third-Party Services"
      ];

      expectedHeadings.forEach(heading => {
        const headingElement = screen.getByRole("heading", { level: 2, name: heading });
        expect(headingElement).toBeInTheDocument();
        expect(headingElement).toHaveClass("text-xl", "font-semibold", "mb-3");
      });
    });

    it("should render system administration notice", () => {
      renderComponent();

      const adminNotice = screen.getByText(/Neuron is Isaac's development project/);
      expect(adminNotice).toBeInTheDocument();

      // Check the notice container styling
      const noticeContainer = adminNotice.closest("div");
      expect(noticeContainer).toHaveClass(
        "bg-blue-50",
        "dark:bg-blue-900/20",
        "border",
        "border-blue-200",
        "dark:border-blue-800",
        "rounded-lg",
        "p-4"
      );
    });

    it("should render data storage explanation", () => {
      renderComponent();

      expect(screen.getByText(/Your data is stored locally in Isaac's homelab infrastructure/)).toBeInTheDocument();
      expect(screen.getByText(/located in his garage/)).toBeInTheDocument();
    });

    it("should render data sharing subsections", () => {
      renderComponent();

      const sharingSubheadings = ["Personalities", "Conversations (Threads)", "Personality Memories"];
      sharingSubheadings.forEach(subheading => {
        const subheadingElement = screen.getByRole("heading", { level: 3, name: subheading });
        expect(subheadingElement).toBeInTheDocument();
        expect(subheadingElement).toHaveClass("font-medium", "mb-2");
      });
    });

    it("should render personality memory warning", () => {
      renderComponent();

      const warningText = screen.getByText(/Important to know:/);
      expect(warningText).toBeInTheDocument();
      expect(warningText).toHaveClass("text-amber-800", "dark:text-amber-200", "text-sm", "font-medium", "mb-1");

      const warningContent = screen.getByText(/If you ask a personality to remember something private/);
      expect(warningContent).toBeInTheDocument();

      // Check warning container styling
      const warningContainer = warningContent.closest("div");
      expect(warningContainer).toHaveClass(
        "bg-amber-50",
        "dark:bg-amber-900/20",
        "border",
        "border-amber-200",
        "dark:border-amber-800",
        "rounded-lg",
        "p-3"
      );
    });

    it("should render cloud service usage subsections", () => {
      renderComponent();

      const cloudSubheadings = ["AI Model Interactions", "Tool Integrations"];
      cloudSubheadings.forEach(subheading => {
        const subheadingElement = screen.getByRole("heading", { level: 3, name: subheading });
        expect(subheadingElement).toBeInTheDocument();
        expect(subheadingElement).toHaveClass("font-medium");
      });
    });

    it("should render AI model interaction details", () => {
      renderComponent();

      expect(screen.getByText(/When you interact with personalities, required data/)).toBeInTheDocument();
      expect(screen.getByText(/Isaac's personal API keys/)).toBeInTheDocument();
      expect(screen.getByText(/Training has been disabled/)).toBeInTheDocument();
    });

    it("should render data control philosophy", () => {
      renderComponent();

      expect(screen.getByText(/The goal of this project is to maintain control/)).toBeInTheDocument();
      expect(screen.getByText(/only sending data to cloud services when absolutely required/)).toBeInTheDocument();
    });

    it("should render future plans section", () => {
      renderComponent();

      expect(screen.getByText(/The long-term goal is to run high-quality AI models/)).toBeInTheDocument();
      expect(screen.getByText(/when it becomes more economically feasible/)).toBeInTheDocument();
    });

    it("should render third-party services information", () => {
      renderComponent();

      expect(screen.getByText(/When your data is processed by external cloud providers/)).toBeInTheDocument();
      expect(screen.getByText(/their respective privacy policies apply/)).toBeInTheDocument();
    });

    it("should render the footer disclaimer", () => {
      renderComponent();

      const footerText = screen.getByText(/This privacy policy reflects the current implementation/);
      expect(footerText).toBeInTheDocument();
      expect(footerText).toHaveClass("text-xs", "text-muted-foreground");

      // Check footer section styling
      const footerSection = footerText.closest("section");
      expect(footerSection).toHaveClass("border-t", "pt-4");
    });
  });

  describe("Warning Boxes and Callouts", () => {
    it("should render admin access notice with proper styling", () => {
      renderComponent();

      const adminText = screen.getByText(/Isaac has full access to the infrastructure/);
      expect(adminText.closest("p")).toHaveClass("text-blue-800", "dark:text-blue-200", "text-sm", "leading-relaxed");
    });

    it("should render personality memory warning with proper styling", () => {
      renderComponent();

      const memoryWarning = screen.getByText(/other users with access to that personality may see that information/);
      expect(memoryWarning.closest("p")).toHaveClass("text-amber-700", "dark:text-amber-300", "text-sm");
    });

    it("should have distinguishable warning colors", () => {
      renderComponent();

      // Admin notice (blue)
      const adminNotice = screen.getByText(/Neuron is Isaac's development project/).closest("div");
      expect(adminNotice).toHaveClass("bg-blue-50", "border-blue-200");

      // Memory warning (amber)
      const memoryWarning = screen.getByText(/Important to know:/).closest("div");
      expect(memoryWarning).toHaveClass("bg-amber-50", "border-amber-200");
    });
  });

  describe("Layout and Styling", () => {
    it("should have proper section spacing", () => {
      renderComponent();

      // Check for section elements (they don't have role="region" by default)
      const sections = document.querySelectorAll("section");
      expect(sections.length).toBeGreaterThan(0);
    });

    it("should have proper text styling for main content", () => {
      renderComponent();

      // Check that main paragraphs exist with the right classes
      const mainParagraphs = document.querySelectorAll("p.text-muted-foreground.leading-relaxed");
      expect(mainParagraphs.length).toBeGreaterThan(0);
    });

    it("should have proper subsection spacing", () => {
      renderComponent();

      const dataSharingSection = screen.getByText("How Data Sharing Works").closest("section");
      const subsectionContainer = dataSharingSection?.querySelector(".space-y-4");
      expect(subsectionContainer).toBeInTheDocument();
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

    it("should have proper content structure for screen readers", () => {
      renderComponent();

      // Check that warning content is properly structured
      const importantText = screen.getByText(/Important to know:/);
      expect(importantText.tagName.toLowerCase()).toBe("p");

      const warningContent = screen.getByText(/If you ask a personality to remember/);
      expect(warningContent.tagName.toLowerCase()).toBe("p");
    });
  });

  describe("Content Completeness", () => {
    it("should mention all key privacy concepts", () => {
      renderComponent();

      // Key privacy concepts that should be mentioned
      const keyTerms = [
        "homelab",
        "API keys",
        "training",
        "memories",
        "sharing",
        "cloud services",
        "data control"
      ];

      keyTerms.forEach(term => {
        const elements = screen.getAllByText(new RegExp(term, "i"));
        expect(elements.length).toBeGreaterThan(0);
      });
    });

    it("should provide specific guidance about data usage", () => {
      renderComponent();

      expect(screen.getByText(/Do not share anything with Neuron that you are not comfortable/)).toBeInTheDocument();
      expect(screen.getByText(/Consider personality memories as shared within the user group/)).toBeInTheDocument();
    });
  });
});
