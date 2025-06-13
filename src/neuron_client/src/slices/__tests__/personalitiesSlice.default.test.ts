import { vi } from 'vitest';
import { configureStore } from "@reduxjs/toolkit";
import personalitiesReducer from "../personalitiesSlice";
import * as actions from "../../actions/personalityActions";
import { Personality } from "../personalitiesSlice.d";

interface TestState {
  personalities: ReturnType<typeof personalitiesReducer>;
}

describe("personalitiesSlice - default personality selection", () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  const createMockPersonality = (id: string, name: string, isDefault = false): Personality => ({
    id,
    name,
    description: `${name} description`,
    context: `${name} context`,
    memory: `${name} memory`,
    tool_set: "default",
    logo: undefined,
    default: isDefault,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });

  it("selects default personality when activePersonalityId is invalid", () => {
    // Set an invalid personality ID in localStorage
    localStorage.setItem("activePersonalityId", "invalid-id");

    const store = configureStore({
      reducer: {
        personalities: personalitiesReducer,
      },
    });

    const personalities = [
      createMockPersonality("p1", "Personality 1"),
      createMockPersonality("p2", "Personality 2", true), // Default
      createMockPersonality("p3", "Personality 3"),
    ];

    // Dispatch fetchPersonalities.fulfilled
    store.dispatch(
      actions.fetchPersonalities.fulfilled(
        { personalities },
        "",
        undefined
      )
    );

    const state = store.getState() as TestState;

    // Should have selected the default personality
    expect(state.personalities.activePersonalityId).toBe("p2");
    expect(localStorage.getItem("activePersonalityId")).toBe("p2");
  });

  it("selects default personality when no activePersonalityId is set", () => {
    const store = configureStore({
      reducer: {
        personalities: personalitiesReducer,
      },
    });

    const personalities = [
      createMockPersonality("p1", "Personality 1"),
      createMockPersonality("p2", "Personality 2", true), // Default
      createMockPersonality("p3", "Personality 3"),
    ];

    // Dispatch fetchPersonalities.fulfilled
    store.dispatch(
      actions.fetchPersonalities.fulfilled(
        { personalities },
        "",
        undefined
      )
    );

    const state = store.getState() as TestState;

    // Should have selected the default personality
    expect(state.personalities.activePersonalityId).toBe("p2");
    expect(localStorage.getItem("activePersonalityId")).toBe("p2");
  });

  it("clears activePersonalityId when invalid and no default exists", () => {
    // Set an invalid personality ID in localStorage
    localStorage.setItem("activePersonalityId", "invalid-id");

    // Re-import the reducer to get fresh initial state with localStorage value
    vi.resetModules();
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { default: freshReducer } = require("../personalitiesSlice");

    const store = configureStore({
      reducer: {
        personalities: freshReducer,
      },
    });

    const personalities = [
      createMockPersonality("p1", "Personality 1"),
      createMockPersonality("p2", "Personality 2"),
      createMockPersonality("p3", "Personality 3"),
    ];

    // Re-import actions too
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { fetchPersonalities } = require("../../actions/personalityActions");

    // Dispatch fetchPersonalities.fulfilled
    store.dispatch(
      fetchPersonalities.fulfilled(
        { personalities },
        "",
        undefined
      )
    );

    const state = store.getState() as TestState;

    // Should have cleared the invalid ID
    expect(state.personalities.activePersonalityId).toBeUndefined();
    expect(localStorage.getItem("activePersonalityId")).toBeNull();
  });

  it("preserves valid activePersonalityId even when default exists", () => {
    // Set a valid personality ID in localStorage
    localStorage.setItem("activePersonalityId", "p1");

    // Re-import the reducer to get fresh initial state with localStorage value
    vi.resetModules();
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { default: freshReducer } = require("../personalitiesSlice");

    const store = configureStore({
      reducer: {
        personalities: freshReducer,
      },
    });

    const personalities = [
      createMockPersonality("p1", "Personality 1"),
      createMockPersonality("p2", "Personality 2", true), // Default
      createMockPersonality("p3", "Personality 3"),
    ];

    // Re-import actions too
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { fetchPersonalities } = require("../../actions/personalityActions");

    // Dispatch fetchPersonalities.fulfilled
    store.dispatch(
      fetchPersonalities.fulfilled(
        { personalities },
        "",
        undefined
      )
    );

    const state = store.getState() as TestState;

    // Should keep the valid active personality
    expect(state.personalities.activePersonalityId).toBe("p1");
    expect(localStorage.getItem("activePersonalityId")).toBe("p1");
  });

  it("only validates after initial fetch", () => {
    // Need to set localStorage before importing the reducer
    localStorage.setItem("activePersonalityId", "invalid-id");

    // Re-import the reducer to get fresh initial state with localStorage value
    vi.resetModules();
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { default: freshReducer } = require("../personalitiesSlice");

    const store = configureStore({
      reducer: {
        personalities: freshReducer,
      },
    });

    // Check initial state - should still have the invalid ID
    let state = store.getState() as TestState;
    expect(state.personalities.activePersonalityId).toBe("invalid-id");
    expect(state.personalities.hasInitiallyFetched).toBe(false);

    // Now fetch personalities
    const personalities = [
      createMockPersonality("p1", "Personality 1"),
      createMockPersonality("p2", "Personality 2", true), // Default
    ];

    // Re-import actions too since we reset modules
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { fetchPersonalities } = require("../../actions/personalityActions");

    store.dispatch(
      fetchPersonalities.fulfilled(
        { personalities },
        "",
        undefined
      )
    );

    state = store.getState() as TestState;

    // After fetch, should have validated and selected default
    expect(state.personalities.hasInitiallyFetched).toBe(true);
    expect(state.personalities.activePersonalityId).toBe("p2");
  });

  it("handles multiple defaults by selecting the first one found", () => {
    const store = configureStore({
      reducer: {
        personalities: personalitiesReducer,
      },
    });

    const personalities = [
      createMockPersonality("p1", "Personality 1"),
      createMockPersonality("p2", "Personality 2", true), // First default
      createMockPersonality("p3", "Personality 3", true), // Second default
    ];

    // Dispatch fetchPersonalities.fulfilled
    store.dispatch(
      actions.fetchPersonalities.fulfilled(
        { personalities },
        "",
        undefined
      )
    );

    const state = store.getState() as TestState;

    // Should have selected the first default found
    expect(state.personalities.activePersonalityId).toBe("p2");
  });
});
