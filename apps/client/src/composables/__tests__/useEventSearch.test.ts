import { describe, it, expect, beforeEach } from 'vitest';
import { useEventSearch } from '../useEventSearch';
import type { HookEvent } from '../../types';

function createMockEvent(overrides: Partial<HookEvent> = {}): HookEvent {
  return {
    source_app: 'prp-framework',
    session_id: 'abc12345-6789-0def',
    hook_event_type: 'PreToolUse',
    payload: {},
    timestamp: Date.now(),
    summary: 'Running bash command',
    model_name: 'claude-opus-4',
    ...overrides,
  } as HookEvent;
}

describe('useEventSearch', () => {
  let search: ReturnType<typeof useEventSearch>;

  beforeEach(() => {
    search = useEventSearch();
  });

  describe('validateRegex', () => {
    it('treats empty string as valid', () => {
      const result = search.validateRegex('');
      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('treats whitespace-only string as valid', () => {
      const result = search.validateRegex('   ');
      expect(result.valid).toBe(true);
    });

    it('accepts valid regex patterns', () => {
      expect(search.validateRegex('hello').valid).toBe(true);
      expect(search.validateRegex('Pre.*Use').valid).toBe(true);
      expect(search.validateRegex('^start').valid).toBe(true);
      expect(search.validateRegex('end$').valid).toBe(true);
      expect(search.validateRegex('[abc]').valid).toBe(true);
      expect(search.validateRegex('foo|bar').valid).toBe(true);
      expect(search.validateRegex('\\d+').valid).toBe(true);
    });

    it('rejects invalid regex patterns', () => {
      const result = search.validateRegex('[unclosed');
      expect(result.valid).toBe(false);
      expect(result.error).toBeDefined();
      expect(typeof result.error).toBe('string');
    });

    it('rejects other invalid regex patterns', () => {
      expect(search.validateRegex('(unclosed').valid).toBe(false);
      expect(search.validateRegex('*invalid').valid).toBe(false);
      expect(search.validateRegex('+invalid').valid).toBe(false);
    });
  });

  describe('matchesPattern', () => {
    it('matches all events when pattern is empty', () => {
      const event = createMockEvent();
      expect(search.matchesPattern(event, '')).toBe(true);
      expect(search.matchesPattern(event, '   ')).toBe(true);
    });

    it('matches case-insensitively', () => {
      const event = createMockEvent({ hook_event_type: 'PreToolUse' });
      expect(search.matchesPattern(event, 'pretooluse')).toBe(true);
      expect(search.matchesPattern(event, 'PRETOOLUSE')).toBe(true);
      expect(search.matchesPattern(event, 'PreToolUse')).toBe(true);
    });

    it('matches against source_app', () => {
      const event = createMockEvent({ source_app: 'my-test-app' });
      expect(search.matchesPattern(event, 'my-test-app')).toBe(true);
    });

    it('matches against session_id', () => {
      const event = createMockEvent({ session_id: 'unique-session-999' });
      expect(search.matchesPattern(event, 'unique-session')).toBe(true);
    });

    it('matches against summary', () => {
      const event = createMockEvent({ summary: 'Executing git commit' });
      expect(search.matchesPattern(event, 'git commit')).toBe(true);
    });

    it('supports regex special characters in pattern', () => {
      const event = createMockEvent({ hook_event_type: 'PreToolUse', summary: 'test123' });
      expect(search.matchesPattern(event, 'Pre.*Use')).toBe(true);
      expect(search.matchesPattern(event, 'test\\d+')).toBe(true);
    });

    it('returns false for invalid regex patterns', () => {
      const event = createMockEvent();
      expect(search.matchesPattern(event, '[unclosed')).toBe(false);
    });

    it('returns false when pattern does not match', () => {
      const event = createMockEvent({ hook_event_type: 'Stop', summary: 'Session ended' });
      expect(search.matchesPattern(event, 'zzz-no-match')).toBe(false);
    });
  });

  describe('searchEvents', () => {
    const events = [
      createMockEvent({ hook_event_type: 'PreToolUse', summary: 'Running bash' }),
      createMockEvent({ hook_event_type: 'PostToolUse', summary: 'Bash completed' }),
      createMockEvent({ hook_event_type: 'Stop', summary: 'Session ended' }),
    ];

    it('returns all events when pattern is empty', () => {
      const result = search.searchEvents(events, '');
      expect(result).toHaveLength(3);
      expect(result).toEqual(events);
    });

    it('filters events matching the pattern', () => {
      const result = search.searchEvents(events, 'bash');
      expect(result).toHaveLength(2);
      expect(result[0].summary).toBe('Running bash');
      expect(result[1].summary).toBe('Bash completed');
    });

    it('returns empty array when no events match', () => {
      const result = search.searchEvents(events, 'zzz-nonexistent');
      expect(result).toHaveLength(0);
    });

    it('filters by hook_event_type', () => {
      const result = search.searchEvents(events, 'Stop');
      expect(result).toHaveLength(1);
      expect(result[0].hook_event_type).toBe('Stop');
    });

    it('supports regex filtering', () => {
      const result = search.searchEvents(events, 'Pre|Post');
      expect(result).toHaveLength(2);
    });
  });

  describe('getSearchableText', () => {
    it('includes hook_event_type', () => {
      const event = createMockEvent({ hook_event_type: 'SessionStart' });
      const text = search.getSearchableText(event);
      expect(text).toContain('sessionstart');
    });

    it('includes source_app', () => {
      const event = createMockEvent({ source_app: 'prp-framework' });
      const text = search.getSearchableText(event);
      expect(text).toContain('prp-framework');
    });

    it('includes session_id', () => {
      const event = createMockEvent({ session_id: 'sess-abc-123' });
      const text = search.getSearchableText(event);
      expect(text).toContain('sess-abc-123');
    });

    it('includes summary', () => {
      const event = createMockEvent({ summary: 'Executing complex operation' });
      const text = search.getSearchableText(event);
      expect(text).toContain('executing complex operation');
    });

    it('returns lowercase text', () => {
      const event = createMockEvent({
        hook_event_type: 'PreToolUse',
        source_app: 'MyApp',
        summary: 'UPPERCASE Summary',
      });
      const text = search.getSearchableText(event);
      expect(text).toBe(text.toLowerCase());
    });

    it('handles event with minimal fields', () => {
      const event: HookEvent = {
        source_app: 'app',
        session_id: 'sess',
        hook_event_type: 'Stop',
        payload: {},
      };
      const text = search.getSearchableText(event);
      expect(text).toContain('stop');
      expect(text).toContain('app');
      expect(text).toContain('sess');
    });
  });

  describe('updateSearchPattern', () => {
    it('sets searchError on invalid regex', () => {
      search.updateSearchPattern('[unclosed');
      expect(search.searchError.value).not.toBe('');
      expect(search.hasError.value).toBe(true);
    });

    it('clears error on valid regex', () => {
      search.updateSearchPattern('[unclosed');
      expect(search.hasError.value).toBe(true);

      search.updateSearchPattern('valid.*pattern');
      expect(search.searchError.value).toBe('');
      expect(search.hasError.value).toBe(false);
    });

    it('clears error when pattern is empty', () => {
      search.updateSearchPattern('[unclosed');
      expect(search.hasError.value).toBe(true);

      search.updateSearchPattern('');
      expect(search.searchError.value).toBe('');
      expect(search.hasError.value).toBe(false);
    });

    it('updates searchPattern ref', () => {
      search.updateSearchPattern('test-pattern');
      expect(search.searchPattern.value).toBe('test-pattern');
    });
  });

  describe('clearSearch', () => {
    it('resets pattern and error', () => {
      search.updateSearchPattern('[invalid');
      expect(search.searchPattern.value).toBe('[invalid');
      expect(search.hasError.value).toBe(true);

      search.clearSearch();
      expect(search.searchPattern.value).toBe('');
      expect(search.searchError.value).toBe('');
      expect(search.hasError.value).toBe(false);
    });
  });
});
