/**
 * PoC: Missing dependency array in useEffect hook.
 *
 * BUG (before fix):
 *   useEffect(() => {
 *     window.addEventListener('message', handleMessages);
 *     return () => { window.removeEventListener('message', handleMessages); };
 *   });  // <-- No dependency array!
 *
 * Without a dependency array, useEffect runs after EVERY render. This means:
 *   1. Every time the component re-renders, a new event listener is added
 *   2. The cleanup runs and removes the old listener, then a new one is added
 *   3. This is wasteful and can cause bugs with stale closures
 *   4. If cleanup timing is off, duplicate listeners accumulate
 *
 * FIX:
 *   useEffect(() => {
 *     window.addEventListener('message', handleMessages);
 *     return () => { window.removeEventListener('message', handleMessages); };
 *   }, []);  // <-- Empty dependency array: runs only once on mount
 *
 * This test verifies the event listener is added exactly once and properly
 * cleaned up, regardless of how many re-renders occur.
 */

import React from 'react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { Provider } from 'react-redux';
import { createMemoryHistory } from 'history';
import { configureStore } from '@reduxjs/toolkit';

import { LocationProvider } from '~/context/Location';
import { reducer } from '~/rootReducer';
import { UPDATE } from '~/modules/user/actions';
import { MockLocalizationProvider } from '~/test/utils';
import { AddonPromotion } from './AddonPromotion';

function createTestStore() {
  const store = configureStore({
    reducer,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({ serializableCheck: false }),
  });
  // Set up authenticated Firefox user who hasn't dismissed the promotion
  store.dispatch({
    type: UPDATE,
    data: {
      is_authenticated: true,
      has_dismissed_addon_promotion: false,
      settings: { force_suggestions: false },
      username: 'testuser',
    },
  });
  return store;
}

function Wrapper({ children, store }) {
  const history = createMemoryHistory({
    initialEntries: ['/kg/firefox/all-resources/'],
  });
  return (
    <Provider store={store}>
      <LocationProvider history={history}>
        <MockLocalizationProvider>{children}</MockLocalizationProvider>
      </LocationProvider>
    </Provider>
  );
}

describe('PoC: AddonPromotion useEffect dependency array', () => {
  let addSpy;
  let removeSpy;
  let originalUserAgent;

  beforeEach(() => {
    addSpy = vi.spyOn(window, 'addEventListener');
    removeSpy = vi.spyOn(window, 'removeEventListener');

    // Mock Firefox user agent so the component renders (not null)
    originalUserAgent = navigator.userAgent;
    Object.defineProperty(navigator, 'userAgent', {
      value: 'Mozilla/5.0 Firefox/120.0',
      configurable: true,
    });
  });

  afterEach(() => {
    cleanup();
    addSpy.mockRestore();
    removeSpy.mockRestore();
    Object.defineProperty(navigator, 'userAgent', {
      value: originalUserAgent,
      configurable: true,
    });
  });

  it('should add the message event listener exactly once on mount', () => {
    const store = createTestStore();

    const { rerender } = render(
      <Wrapper store={store}>
        <AddonPromotion />
      </Wrapper>,
    );

    // Count how many times addEventListener was called with 'message'
    const messageListenerCalls = addSpy.mock.calls.filter(
      ([event]) => event === 'message',
    );

    expect(messageListenerCalls).toHaveLength(1);

    // Force a re-render by re-rendering with same props
    rerender(
      <Wrapper store={store}>
        <AddonPromotion />
      </Wrapper>,
    );

    // After fix: should STILL be just 1 call (useEffect with [] only runs once)
    // Before fix (no deps array): would be 2 calls (runs on every render)
    const messageListenerCallsAfterRerender = addSpy.mock.calls.filter(
      ([event]) => event === 'message',
    );

    expect(messageListenerCallsAfterRerender).toHaveLength(1);
  });

  it('should clean up the message event listener on unmount', () => {
    const store = createTestStore();

    const { unmount } = render(
      <Wrapper store={store}>
        <AddonPromotion />
      </Wrapper>,
    );

    // Unmount the component
    unmount();

    // Should have removed the 'message' listener exactly once
    const removeMessageCalls = removeSpy.mock.calls.filter(
      ([event]) => event === 'message',
    );

    expect(removeMessageCalls).toHaveLength(1);
  });
});
