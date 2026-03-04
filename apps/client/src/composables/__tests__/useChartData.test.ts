import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useChartData } from '../useChartData';
import type { HookEvent } from '../../types';

function createMockEvent(overrides: Partial<HookEvent> = {}): HookEvent {
  return {
    source_app: 'prp-framework',
    session_id: 'abcd1234-5678-90ef',
    hook_event_type: 'PreToolUse',
    payload: { tool_name: 'Bash' },
    timestamp: Date.now(),
    summary: 'Running command',
    ...overrides,
  } as HookEvent;
}

describe('useChartData', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('addEvent + getChartData', () => {
    it('adds events and populates data points after debounce', () => {
      const { addEvent, getChartData, dataPoints } = useChartData();

      const now = Date.now();
      addEvent(createMockEvent({ timestamp: now }));
      addEvent(createMockEvent({ timestamp: now + 100 }));

      // Before debounce fires, dataPoints should be empty
      expect(dataPoints.value).toHaveLength(0);

      // Advance past 50ms debounce
      vi.advanceTimersByTime(60);

      // Now data should be processed
      expect(dataPoints.value.length).toBeGreaterThan(0);

      // getChartData fills all buckets in the time window
      const chartData = getChartData();
      expect(chartData.length).toBeGreaterThan(0);

      // At least one bucket should have a non-zero count
      const nonZeroBuckets = chartData.filter(dp => dp.count > 0);
      expect(nonZeroBuckets.length).toBeGreaterThan(0);
    });

    it('groups events into the same bucket when close together', () => {
      const { addEvent, dataPoints } = useChartData();

      // Use a timestamp floored to a 1-second boundary to ensure both fall in the same bucket
      const bucketStart = Math.floor(Date.now() / 1000) * 1000;
      // Both events within the same 1-second bucket (default 1m range = 1s buckets)
      addEvent(createMockEvent({ timestamp: bucketStart + 100 }));
      addEvent(createMockEvent({ timestamp: bucketStart + 300 }));

      vi.advanceTimersByTime(60);

      // Should be in one bucket (same second)
      expect(dataPoints.value).toHaveLength(1);
      expect(dataPoints.value[0].count).toBe(2);
    });

    it('tracks event types in data points', () => {
      const { addEvent, dataPoints } = useChartData();

      const now = Date.now();
      addEvent(createMockEvent({ timestamp: now, hook_event_type: 'PreToolUse' }));
      addEvent(createMockEvent({ timestamp: now + 100, hook_event_type: 'PostToolUse' }));

      vi.advanceTimersByTime(60);

      expect(dataPoints.value).toHaveLength(1);
      expect(dataPoints.value[0].eventTypes['PreToolUse']).toBe(1);
      expect(dataPoints.value[0].eventTypes['PostToolUse']).toBe(1);
    });

    it('skips events without timestamp', () => {
      const { addEvent, dataPoints } = useChartData();

      addEvent(createMockEvent({ timestamp: undefined }));

      vi.advanceTimersByTime(60);

      expect(dataPoints.value).toHaveLength(0);
    });
  });

  describe('clearData', () => {
    it('resets all data', () => {
      const { addEvent, clearData, dataPoints } = useChartData();

      const now = Date.now();
      addEvent(createMockEvent({ timestamp: now }));
      vi.advanceTimersByTime(60);

      expect(dataPoints.value.length).toBeGreaterThan(0);

      clearData();

      expect(dataPoints.value).toHaveLength(0);
    });
  });

  describe('setTimeRange', () => {
    it('changes the time range', () => {
      const { setTimeRange, timeRange, currentConfig } = useChartData();

      expect(timeRange.value).toBe('1m');
      expect(currentConfig.value.bucketSize).toBe(1000);

      setTimeRange('3m');
      expect(timeRange.value).toBe('3m');
      expect(currentConfig.value.bucketSize).toBe(3000);

      setTimeRange('5m');
      expect(timeRange.value).toBe('5m');
      expect(currentConfig.value.bucketSize).toBe(5000);

      setTimeRange('10m');
      expect(timeRange.value).toBe('10m');
      expect(currentConfig.value.bucketSize).toBe(10000);
    });
  });

  describe('getChartData', () => {
    it('returns array with filled buckets for the time window', () => {
      const { getChartData } = useChartData();

      const chartData = getChartData();

      // Should have up to 60 buckets (maxPoints)
      expect(chartData.length).toBeLessThanOrEqual(60);
      expect(chartData.length).toBeGreaterThan(0);

      // All buckets should have count property (0 for empty)
      chartData.forEach(dp => {
        expect(dp.count).toBeGreaterThanOrEqual(0);
        expect(dp.timestamp).toBeDefined();
        expect(dp.eventTypes).toBeDefined();
        expect(dp.sessions).toBeDefined();
      });
    });

    it('fills empty buckets with count 0', () => {
      const { getChartData } = useChartData();

      const chartData = getChartData();
      // With no events, all buckets should have count 0
      chartData.forEach(dp => {
        expect(dp.count).toBe(0);
      });
    });

    it('includes events that were added', () => {
      const { addEvent, getChartData } = useChartData();

      const now = Date.now();
      addEvent(createMockEvent({ timestamp: now }));
      vi.advanceTimersByTime(60);

      const chartData = getChartData();
      const totalCount = chartData.reduce((sum, dp) => sum + dp.count, 0);
      expect(totalCount).toBe(1);
    });
  });

  describe('uniqueAgentCount', () => {
    it('counts distinct agents', () => {
      const { addEvent, uniqueAgentCount } = useChartData();

      const now = Date.now();
      // Same agent (same source_app + session_id)
      addEvent(createMockEvent({ timestamp: now, source_app: 'app1', session_id: 'session-a-1234' }));
      addEvent(createMockEvent({ timestamp: now + 100, source_app: 'app1', session_id: 'session-a-1234' }));

      vi.advanceTimersByTime(60);
      expect(uniqueAgentCount.value).toBe(1);
    });

    it('counts different agents separately', () => {
      const { addEvent, uniqueAgentCount } = useChartData();

      const now = Date.now();
      addEvent(createMockEvent({ timestamp: now, source_app: 'app1', session_id: 'session-a-1111' }));
      addEvent(createMockEvent({ timestamp: now + 100, source_app: 'app2', session_id: 'session-b-2222' }));

      vi.advanceTimersByTime(60);
      expect(uniqueAgentCount.value).toBe(2);
    });

    it('distinguishes agents by session_id prefix', () => {
      const { addEvent, uniqueAgentCount } = useChartData();

      const now = Date.now();
      // Same app but different session IDs (different first 8 chars)
      addEvent(createMockEvent({ timestamp: now, source_app: 'app1', session_id: 'aaaaaaaa-rest' }));
      addEvent(createMockEvent({ timestamp: now + 100, source_app: 'app1', session_id: 'bbbbbbbb-rest' }));

      vi.advanceTimersByTime(60);
      expect(uniqueAgentCount.value).toBe(2);
    });
  });

  describe('toolCallCount', () => {
    it('counts PreToolUse events', () => {
      const { addEvent, toolCallCount } = useChartData();

      const now = Date.now();
      addEvent(createMockEvent({ timestamp: now, hook_event_type: 'PreToolUse' }));
      addEvent(createMockEvent({ timestamp: now + 100, hook_event_type: 'PreToolUse' }));
      addEvent(createMockEvent({ timestamp: now + 200, hook_event_type: 'PostToolUse' }));
      addEvent(createMockEvent({ timestamp: now + 300, hook_event_type: 'Stop' }));

      vi.advanceTimersByTime(60);

      expect(toolCallCount.value).toBe(2);
    });

    it('returns 0 when no PreToolUse events', () => {
      const { addEvent, toolCallCount } = useChartData();

      const now = Date.now();
      addEvent(createMockEvent({ timestamp: now, hook_event_type: 'Stop' }));
      addEvent(createMockEvent({ timestamp: now + 100, hook_event_type: 'SessionStart' }));

      vi.advanceTimersByTime(60);

      expect(toolCallCount.value).toBe(0);
    });
  });

  describe('agentIdFilter', () => {
    it('filters events by agent ID', () => {
      const { addEvent, dataPoints } = useChartData('app1:session1');

      const now = Date.now();
      // Matching event: source_app=app1, session_id starts with "session1"
      addEvent(createMockEvent({ timestamp: now, source_app: 'app1', session_id: 'session1-extra-data' }));
      // Non-matching event: different app
      addEvent(createMockEvent({ timestamp: now + 100, source_app: 'app2', session_id: 'session1-extra-data' }));

      vi.advanceTimersByTime(60);

      const totalCount = dataPoints.value.reduce((sum, dp) => sum + dp.count, 0);
      expect(totalCount).toBe(1);
    });
  });

  describe('cleanup', () => {
    it('processes remaining buffered events on cleanup', () => {
      const { addEvent, cleanup, dataPoints } = useChartData();

      const now = Date.now();
      addEvent(createMockEvent({ timestamp: now }));

      // Don't wait for debounce -- call cleanup directly
      cleanup();

      expect(dataPoints.value.length).toBeGreaterThan(0);
    });
  });
});
