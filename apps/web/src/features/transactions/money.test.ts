import { describe, expect, it } from 'vitest';
import { centsToInput, formatCad, parseCadToCents } from './money';

describe('transaction money boundary', () => {
  it('parses plain decimal text into exact signed cents', () => {
    expect(parseCadToCents('42')).toBe(4200);
    expect(parseCadToCents('42.5')).toBe(4250);
    expect(parseCadToCents('-0.25')).toBe(-25);
  });

  it('rejects zero, exponent, grouping, and excess precision', () => {
    expect(parseCadToCents('0')).toBeNull();
    expect(parseCadToCents('1e3')).toBeNull();
    expect(parseCadToCents('1,000')).toBeNull();
    expect(parseCadToCents('12.345')).toBeNull();
  });

  it('formats cents at the presentation edge', () => {
    expect(centsToInput(-4250)).toBe('-42.50');
    expect(formatCad(123456)).toBe('$1,234.56');
  });
});
