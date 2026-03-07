/**
 * PoC: Incorrect useEffect dependency [!openImage] in Screenshots component.
 *
 * BUG (before fix):
 *   useEffect(() => {
 *     if (!openImage) return;
 *     const handleKeyDown = ...;
 *     window.document.addEventListener('keydown', handleKeyDown);
 *     return () => { window.document.removeEventListener('keydown', handleKeyDown); };
 *   }, [!openImage]);  // <-- WRONG: boolean negation coerces to boolean
 *
 * The dependency `[!openImage]` evaluates to `[true]` when openImage is null
 * and `[false]` when openImage is a string. This means:
 *   1. React only sees boolean transitions (true -> false, false -> true)
 *   2. If openImage changes from one URL to another URL, `!openImage` stays
 *      `false` both times, so the effect doesn't re-run
 *   3. The keyboard handler captures the old URL in its closure
 *
 * FIX:
 *   useEffect(() => { ... }, [openImage]);  // <-- Track actual value
 *
 * This ensures the effect re-runs whenever the actual openImage value changes.
 */

import React from 'react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { act } from 'react-dom/test-utils';
import { mount } from 'enzyme';
import { Screenshots } from './Screenshots';

describe('PoC: Screenshots useEffect dependency [!openImage] vs [openImage]', () => {
  let addSpy;
  let removeSpy;

  beforeEach(() => {
    addSpy = vi.spyOn(window.document, 'addEventListener');
    removeSpy = vi.spyOn(window.document, 'removeEventListener');
  });

  afterEach(() => {
    addSpy.mockRestore();
    removeSpy.mockRestore();
  });

  it('should register keydown listener when lightbox opens', () => {
    const source = 'Image URL: http://example.com/image1.png';
    const wrapper = mount(<Screenshots locale='kg' source={source} />);

    // Initially, no keydown listener should be registered
    const keydownCallsBefore = addSpy.mock.calls.filter(
      ([event]) => event === 'keydown',
    );
    expect(keydownCallsBefore).toHaveLength(0);

    // Click to open lightbox
    wrapper.find('img').simulate('click');

    // Now keydown listener should be registered
    const keydownCallsAfter = addSpy.mock.calls.filter(
      ([event]) => event === 'keydown',
    );
    expect(keydownCallsAfter).toHaveLength(1);
  });

  it('should clean up keydown listener when lightbox closes', () => {
    const source = 'Image URL: http://example.com/image1.png';
    const wrapper = mount(<Screenshots locale='kg' source={source} />);

    // Open lightbox
    wrapper.find('img').simulate('click');

    // Close lightbox via click
    wrapper.find('.lightbox').simulate('click');

    // Keydown listener should be removed
    const removeKeydownCalls = removeSpy.mock.calls.filter(
      ([event]) => event === 'keydown',
    );
    expect(removeKeydownCalls).toHaveLength(1);
  });

  it('should close lightbox on Escape key press', () => {
    const source = 'Image URL: http://example.com/image1.png';
    const wrapper = mount(<Screenshots locale='kg' source={source} />);

    // Open lightbox
    wrapper.find('img').simulate('click');
    expect(wrapper.find('.lightbox')).toHaveLength(1);

    // Press Escape
    act(() => {
      window.document.dispatchEvent(
        new KeyboardEvent('keydown', { code: 'Escape' }),
      );
    });
    wrapper.update();

    // Lightbox should be closed
    expect(wrapper.find('.lightbox')).toHaveLength(0);
  });

  it('should handle multiple open/close cycles correctly', () => {
    const source =
      'Two images: http://example.com/img1.png and http://example.com/img2.png';
    const wrapper = mount(<Screenshots locale='kg' source={source} />);

    // Cycle 1: Open first image
    wrapper.find('img').at(0).simulate('click');
    expect(wrapper.find('.lightbox')).toHaveLength(1);

    // Close via keyboard
    act(() => {
      window.document.dispatchEvent(
        new KeyboardEvent('keydown', { code: 'Escape' }),
      );
    });
    wrapper.update();
    expect(wrapper.find('.lightbox')).toHaveLength(0);

    // Cycle 2: Open second image
    wrapper.find('img').at(1).simulate('click');
    expect(wrapper.find('.lightbox')).toHaveLength(1);

    // Close via keyboard again — this should still work
    // With the old [!openImage] bug, this could fail because
    // !openImage was false both times (string -> string), so
    // the effect might not re-run to register a new handler
    act(() => {
      window.document.dispatchEvent(
        new KeyboardEvent('keydown', { code: 'Space' }),
      );
    });
    wrapper.update();
    expect(wrapper.find('.lightbox')).toHaveLength(0);
  });
});
