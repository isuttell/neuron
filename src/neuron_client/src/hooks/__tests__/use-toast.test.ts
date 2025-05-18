import { reducer } from "../use-toast";

// We'll focus on testing the reducer since the hook implementation is complex
// and uses global state that makes it challenging to test in isolation
describe("toast reducer", () => {
  it("should handle ADD_TOAST action", () => {
    const initialState = { toasts: [] };
    const toast = { id: "1", title: "Test Toast", open: true };

    const newState = reducer(initialState, {
      type: "ADD_TOAST",
      toast,
    });

    expect(newState.toasts).toEqual([toast]);
  });

  it("should handle UPDATE_TOAST action", () => {
    const initialState = {
      toasts: [{ id: "1", title: "Initial Toast", open: true }],
    };

    const newState = reducer(initialState, {
      type: "UPDATE_TOAST",
      toast: { id: "1", title: "Updated Toast" },
    });

    expect(newState.toasts[0].title).toBe("Updated Toast");
    expect(newState.toasts[0].open).toBe(true); // Should preserve existing properties
  });

  it("should handle DISMISS_TOAST action for a specific toast", () => {
    const initialState = {
      toasts: [
        { id: "1", title: "Toast 1", open: true },
        { id: "2", title: "Toast 2", open: true },
      ],
    };

    const newState = reducer(initialState, {
      type: "DISMISS_TOAST",
      toastId: "1",
    });

    expect(newState.toasts[0].open).toBe(false); // First toast should be closed
    expect(newState.toasts[1].open).toBe(true); // Second toast should remain open
  });

  it("should handle DISMISS_TOAST action for all toasts", () => {
    const initialState = {
      toasts: [
        { id: "1", title: "Toast 1", open: true },
        { id: "2", title: "Toast 2", open: true },
      ],
    };

    const newState = reducer(initialState, {
      type: "DISMISS_TOAST",
    });

    expect(newState.toasts.every(t => t.open === false)).toBe(true);
  });

  it("should handle REMOVE_TOAST action for a specific toast", () => {
    const initialState = {
      toasts: [
        { id: "1", title: "Toast 1", open: true },
        { id: "2", title: "Toast 2", open: true },
      ],
    };

    const newState = reducer(initialState, {
      type: "REMOVE_TOAST",
      toastId: "1",
    });

    expect(newState.toasts.length).toBe(1);
    expect(newState.toasts[0].id).toBe("2");
  });

  it("should handle REMOVE_TOAST action for all toasts", () => {
    const initialState = {
      toasts: [
        { id: "1", title: "Toast 1", open: true },
        { id: "2", title: "Toast 2", open: true },
      ],
    };

    const newState = reducer(initialState, {
      type: "REMOVE_TOAST",
    });

    expect(newState.toasts.length).toBe(0);
  });

  it("should limit the number of toasts to TOAST_LIMIT", () => {
    const initialState = { toasts: [] };

    // Add multiple toasts
    let state = reducer(initialState, {
      type: "ADD_TOAST",
      toast: { id: "1", title: "Toast 1", open: true },
    });

    state = reducer(state, {
      type: "ADD_TOAST",
      toast: { id: "2", title: "Toast 2", open: true },
    });

    // TOAST_LIMIT is 1 in the component, so only Toast 2 should remain
    expect(state.toasts.length).toBe(1);
    expect(state.toasts[0].id).toBe("2");
  });
});
