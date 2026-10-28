import { describe, it, expect } from 'vitest';
import { deriveWsUrl } from '../utils/url';

describe('deriveWsUrl', () => {
  it('returns explicit env URL when provided', () => {
    expect(deriveWsUrl('ws://custom-host:9999')).toBe('ws://custom-host:9999');
    expect(deriveWsUrl('wss://secure.sim.io/relay')).toBe('wss://secure.sim.io/relay');
  });

  it('ignores empty or whitespace env URL and falls back', () => {
    const fallback = deriveWsUrl('   ', { protocol: 'http:', hostname: '10.0.0.5' });
    expect(fallback).toBe('ws://10.0.0.5:8080');
  });

  it('derives ws:// URL from http location', () => {
    const loc = { protocol: 'http:', hostname: 'localhost' };
    expect(deriveWsUrl(undefined, loc)).toBe('ws://localhost:8080');
  });

  it('derives wss:// URL from https location', () => {
    const loc = { protocol: 'https:', hostname: 'swarm.company.org' };
    expect(deriveWsUrl(undefined, loc)).toBe('wss://swarm.company.org:8080');
  });

  it('defaults to ws://localhost:8080 when no location is available', () => {
    expect(deriveWsUrl(undefined, null)).toBe('ws://localhost:8080');
  });
});
