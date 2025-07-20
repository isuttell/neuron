import { configureStore } from '@reduxjs/toolkit';
import appSlice, {
  setBuildHashMismatch,
  getBuildHashMismatch,
} from '../appSlice';

describe('appSlice build hash functionality', () => {
  let store: ReturnType<typeof configureStore>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        app: appSlice,
      },
    });
  });

  describe('setBuildHashMismatch', () => {
    it('sets build hash mismatch to true', () => {
      store.dispatch(setBuildHashMismatch(true));

      const state = store.getState();
      expect(getBuildHashMismatch(state)).toBe(true);
    });

    it('sets build hash mismatch to false', () => {
      // First set to true
      store.dispatch(setBuildHashMismatch(true));
      expect(getBuildHashMismatch(store.getState())).toBe(true);

      // Then set to false
      store.dispatch(setBuildHashMismatch(false));
      expect(getBuildHashMismatch(store.getState())).toBe(false);
    });

    it('does not save to localStorage', () => {
      const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');

      store.dispatch(setBuildHashMismatch(true));

      // Should not call setItem because this is session-specific
      expect(setItemSpy).not.toHaveBeenCalled();

      setItemSpy.mockRestore();
    });
  });


  describe('initial state', () => {
    it('initializes build hash state correctly', () => {
      const state = store.getState();

      expect(getBuildHashMismatch(state)).toBe(false);
    });
  });

  describe('selectors', () => {
    beforeEach(() => {
      store.dispatch(setBuildHashMismatch(true));
    });

    it('getBuildHashMismatch returns correct value', () => {
      const state = store.getState();
      expect(getBuildHashMismatch(state)).toBe(true);
    });
  });

  describe('state persistence', () => {
    it('does not persist build hash related state to localStorage', () => {
      const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');

      // Dispatch build hash action
      store.dispatch(setBuildHashMismatch(true));

      // Should not trigger localStorage save
      expect(setItemSpy).not.toHaveBeenCalled();

      setItemSpy.mockRestore();
    });

    it('only persists non-session specific state', () => {
      const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');

      // This should trigger localStorage save (not session-specific)
      store.dispatch({ type: 'app/setSidebarImage', payload: 'new-image.jpg' });

      expect(setItemSpy).toHaveBeenCalled();

      // Reset and test build hash actions don't save
      setItemSpy.mockClear();
      store.dispatch(setBuildHashMismatch(true));

      expect(setItemSpy).not.toHaveBeenCalled();

      setItemSpy.mockRestore();
    });
  });
});
