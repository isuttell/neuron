import { configureStore } from "@reduxjs/toolkit";
import personalitiesReducer, { setActivePersonality } from "../personalitiesSlice";

interface TestState {
  personalities: ReturnType<typeof personalitiesReducer>;
}

describe("personalitiesSlice - activePersonalityId localStorage handling", () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  it("removes activePersonalityId from localStorage when set to undefined", () => {
    // Set initial value in localStorage
    localStorage.setItem("activePersonalityId", "test-id");

    const store = configureStore({
      reducer: {
        personalities: personalitiesReducer,
      },
    });

    // Dispatch action to set activePersonalityId to undefined
    store.dispatch(setActivePersonality(undefined));

    // Check that localStorage was cleared
    expect(localStorage.getItem("activePersonalityId")).toBeNull();

    // Check that state was updated
    const state = store.getState() as TestState;
    expect(state.personalities.activePersonalityId).toBeUndefined();
  });

  it("sets activePersonalityId in localStorage when given a valid ID", () => {
    const store = configureStore({
      reducer: {
        personalities: personalitiesReducer,
      },
    });

    // Dispatch action to set activePersonalityId
    store.dispatch(setActivePersonality("personality-123"));

    // Check that localStorage was set
    expect(localStorage.getItem("activePersonalityId")).toBe("personality-123");

    // Check that state was updated
    const state = store.getState() as TestState;
    expect(state.personalities.activePersonalityId).toBe("personality-123");
  });

  it("handles localStorage initialization edge cases", () => {
    // Test 1: When localStorage has no value, activePersonalityId should be undefined
    localStorage.clear();

    // Need to re-import the reducer to get fresh initial state
    jest.resetModules();
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { default: freshReducer } = require("../personalitiesSlice");

    const store = configureStore({
      reducer: {
        personalities: freshReducer,
      },
    });

    const state = store.getState() as TestState;
    expect(state.personalities.activePersonalityId).toBeUndefined();
  });
});
