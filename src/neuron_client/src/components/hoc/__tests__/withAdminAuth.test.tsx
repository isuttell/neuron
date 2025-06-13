import { vi } from 'vitest';
import { render, screen } from "@testing-library/react";
import { User, Auth0ContextInterface } from "@auth0/auth0-react";
import { withAdminAuth } from "../withAdminAuth";
import * as auth0React from "@auth0/auth0-react";

// Mock Auth0 hook
vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

// Test component
const TestComponent = () => <div>Test Component Content</div>;

describe("withAdminAuth", () => {
  const mockUseAuth0 = vi.spyOn(auth0React, "useAuth0");

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("when user is admin", () => {
    beforeEach(() => {
      const mockUser = {
        "neuron/roles": ["admin", "user"],
      } as User;

      mockUseAuth0.mockReturnValue({
        user: mockUser,
      } as Auth0ContextInterface<User>);
    });

    it("renders the wrapped component", () => {
      const WrappedComponent = withAdminAuth(TestComponent);
      render(<WrappedComponent />);

      expect(screen.getByText("Test Component Content")).toBeInTheDocument();
    });

    it("renders the wrapped component with showMessage=true", () => {
      const WrappedComponent = withAdminAuth(TestComponent, true);
      render(<WrappedComponent />);

      expect(screen.getByText("Test Component Content")).toBeInTheDocument();
    });
  });

  describe("when user is not admin", () => {
    beforeEach(() => {
      const mockUser = {
        "neuron/roles": ["user"],
      } as User;

      mockUseAuth0.mockReturnValue({
        user: mockUser,
      } as Auth0ContextInterface<User>);
    });

    it("renders null when showMessage=false (default)", () => {
      const WrappedComponent = withAdminAuth(TestComponent);
      const { container } = render(<WrappedComponent />);

      expect(container.firstChild).toBeNull();
      expect(screen.queryByText("Test Component Content")).not.toBeInTheDocument();
    });

    it("renders access forbidden message when showMessage=true", () => {
      const WrappedComponent = withAdminAuth(TestComponent, true);
      render(<WrappedComponent />);

      expect(screen.getByText("Access Forbidden")).toBeInTheDocument();
      expect(screen.getByText("You need administrator privileges to view this page.")).toBeInTheDocument();
      expect(screen.queryByText("Test Component Content")).not.toBeInTheDocument();
    });
  });

  describe("when user has no roles", () => {
    beforeEach(() => {
      const mockUser = {
        "neuron/roles": [],
      } as User;

      mockUseAuth0.mockReturnValue({
        user: mockUser,
      } as Auth0ContextInterface<User>);
    });

    it("renders null when showMessage=false", () => {
      const WrappedComponent = withAdminAuth(TestComponent);
      const { container } = render(<WrappedComponent />);

      expect(container.firstChild).toBeNull();
    });

    it("renders access forbidden message when showMessage=true", () => {
      const WrappedComponent = withAdminAuth(TestComponent, true);
      render(<WrappedComponent />);

      expect(screen.getByText("Access Forbidden")).toBeInTheDocument();
    });
  });

  describe("when user is undefined", () => {
    beforeEach(() => {
      mockUseAuth0.mockReturnValue({
        user: undefined,
      } as Auth0ContextInterface<User>);
    });

    it("renders null when showMessage=false", () => {
      const WrappedComponent = withAdminAuth(TestComponent);
      const { container } = render(<WrappedComponent />);

      expect(container.firstChild).toBeNull();
    });

    it("renders access forbidden message when showMessage=true", () => {
      const WrappedComponent = withAdminAuth(TestComponent, true);
      render(<WrappedComponent />);

      expect(screen.getByText("Access Forbidden")).toBeInTheDocument();
    });
  });

  describe("component props", () => {
    it("passes props to the wrapped component when user is admin", () => {
      const mockUser = {
        "neuron/roles": ["admin"],
      } as User;

      mockUseAuth0.mockReturnValue({
        user: mockUser,
      } as Auth0ContextInterface<User>);

      const TestComponentWithProps = ({ testProp }: { testProp: string }) => (
        <div>Test Component with {testProp}</div>
      );

      const WrappedComponent = withAdminAuth(TestComponentWithProps);
      render(<WrappedComponent testProp="test value" />);

      expect(screen.getByText("Test Component with test value")).toBeInTheDocument();
    });
  });

  describe("display name", () => {
    it("sets correct display name for wrapped component", () => {
      const TestComponentWithName = () => <div>Test</div>;
      TestComponentWithName.displayName = "TestComponentWithName";

      const WrappedComponent = withAdminAuth(TestComponentWithName);

      expect(WrappedComponent.name).toBe("WithAdminAuthComponent");
    });
  });
});
