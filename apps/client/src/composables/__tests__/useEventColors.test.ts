import { describe, it, expect } from 'vitest';
import { useEventColors } from '../useEventColors';

describe('useEventColors', () => {
  const {
    getColorForSession,
    getColorForApp,
    getGradientForSession,
    getGradientForApp,
    getHexColorForSession,
    getHexColorForApp,
  } = useEventColors();

  describe('getColorForSession', () => {
    it('returns a valid Tailwind bg-*-500 class', () => {
      const color = getColorForSession('session-abc-123');
      expect(color).toMatch(/^bg-\w+-500$/);
    });

    it('is deterministic - same input gives same output', () => {
      const color1 = getColorForSession('test-session-id');
      const color2 = getColorForSession('test-session-id');
      expect(color1).toBe(color2);
    });

    it('can give different outputs for different inputs', () => {
      const colors = new Set<string>();
      const inputs = [
        'session-aaa',
        'session-bbb',
        'session-ccc',
        'session-ddd',
        'session-eee',
        'session-fff',
        'session-ggg',
        'session-hhh',
        'session-iii',
        'session-jjj',
        'session-kkk',
      ];
      inputs.forEach(input => {
        colors.add(getColorForSession(input));
      });
      // With 11 inputs and 10 colors, we should get at least 2 different colors
      expect(colors.size).toBeGreaterThan(1);
    });

    it('handles empty string input', () => {
      const color = getColorForSession('');
      expect(color).toMatch(/^bg-\w+-500$/);
    });

    it('handles very long string input', () => {
      const longString = 'a'.repeat(10000);
      const color = getColorForSession(longString);
      expect(color).toMatch(/^bg-\w+-500$/);
    });
  });

  describe('getColorForApp', () => {
    it('returns a valid Tailwind bg-*-500 class', () => {
      const color = getColorForApp('prp-framework');
      expect(color).toMatch(/^bg-\w+-500$/);
    });

    it('is deterministic - same input gives same output', () => {
      const color1 = getColorForApp('my-app');
      const color2 = getColorForApp('my-app');
      expect(color1).toBe(color2);
    });

    it('can give different outputs for different inputs', () => {
      const colors = new Set<string>();
      const inputs = ['app-alpha', 'app-beta', 'app-gamma', 'app-delta', 'app-epsilon',
        'app-zeta', 'app-eta', 'app-theta', 'app-iota', 'app-kappa', 'app-lambda'];
      inputs.forEach(input => {
        colors.add(getColorForApp(input));
      });
      expect(colors.size).toBeGreaterThan(1);
    });

    it('handles empty string input', () => {
      const color = getColorForApp('');
      expect(color).toMatch(/^bg-\w+-500$/);
    });

    it('handles very long string input', () => {
      const longString = 'x'.repeat(10000);
      const color = getColorForApp(longString);
      expect(color).toMatch(/^bg-\w+-500$/);
    });
  });

  describe('getGradientForSession', () => {
    it('returns a gradient class string containing "bg-gradient-to-r"', () => {
      const gradient = getGradientForSession('session-123');
      expect(gradient).toContain('bg-gradient-to-r');
    });

    it('returns a string with from-* and to-* classes', () => {
      const gradient = getGradientForSession('session-123');
      expect(gradient).toMatch(/from-\w+-500/);
      expect(gradient).toMatch(/to-\w+-600/);
    });

    it('is deterministic', () => {
      const g1 = getGradientForSession('same-session');
      const g2 = getGradientForSession('same-session');
      expect(g1).toBe(g2);
    });

    it('handles empty string input', () => {
      const gradient = getGradientForSession('');
      expect(gradient).toContain('bg-gradient-to-r');
    });

    it('handles very long string input', () => {
      const gradient = getGradientForSession('z'.repeat(10000));
      expect(gradient).toContain('bg-gradient-to-r');
    });
  });

  describe('getGradientForApp', () => {
    it('returns a gradient class string containing "bg-gradient-to-r"', () => {
      const gradient = getGradientForApp('my-app');
      expect(gradient).toContain('bg-gradient-to-r');
    });

    it('returns a string with from-* and to-* classes', () => {
      const gradient = getGradientForApp('my-app');
      expect(gradient).toMatch(/from-\w+-500/);
      expect(gradient).toMatch(/to-\w+-600/);
    });

    it('is deterministic', () => {
      const g1 = getGradientForApp('same-app');
      const g2 = getGradientForApp('same-app');
      expect(g1).toBe(g2);
    });
  });

  describe('getHexColorForSession', () => {
    it('returns a hex color string starting with "#"', () => {
      const hex = getHexColorForSession('session-abc');
      expect(hex).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });

    it('is deterministic', () => {
      const h1 = getHexColorForSession('same-session');
      const h2 = getHexColorForSession('same-session');
      expect(h1).toBe(h2);
    });

    it('handles empty string input', () => {
      const hex = getHexColorForSession('');
      expect(hex).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });

    it('handles very long string input', () => {
      const hex = getHexColorForSession('q'.repeat(10000));
      expect(hex).toMatch(/^#[0-9A-Fa-f]{6}$/);
    });
  });

  describe('getHexColorForApp', () => {
    it('returns an hsl() color string', () => {
      const hsl = getHexColorForApp('prp-framework');
      expect(hsl).toMatch(/^hsl\(\d+, 70%, 50%\)$/);
    });

    it('is deterministic', () => {
      const h1 = getHexColorForApp('same-app');
      const h2 = getHexColorForApp('same-app');
      expect(h1).toBe(h2);
    });

    it('hue is within 0-359 range', () => {
      const hsl = getHexColorForApp('test-app');
      const match = hsl.match(/^hsl\((\d+), 70%, 50%\)$/);
      expect(match).not.toBeNull();
      const hue = parseInt(match![1], 10);
      expect(hue).toBeGreaterThanOrEqual(0);
      expect(hue).toBeLessThan(360);
    });

    it('handles empty string input', () => {
      const hsl = getHexColorForApp('');
      expect(hsl).toMatch(/^hsl\(\d+, 70%, 50%\)$/);
    });

    it('handles very long string input', () => {
      const hsl = getHexColorForApp('m'.repeat(10000));
      expect(hsl).toMatch(/^hsl\(\d+, 70%, 50%\)$/);
    });

    it('can produce different hues for different inputs', () => {
      const hues = new Set<string>();
      const inputs = ['app-1', 'app-2', 'app-3', 'app-4', 'app-5',
        'app-6', 'app-7', 'app-8', 'app-9', 'app-10'];
      inputs.forEach(input => {
        hues.add(getHexColorForApp(input));
      });
      expect(hues.size).toBeGreaterThan(1);
    });
  });
});
