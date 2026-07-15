import type { Direction } from './types';
import aurora from './aurora';
import ledger from './ledger';
import horizon from './horizon';

export const directions: Direction[] = [aurora, ledger, horizon];

export const directionById: Record<string, Direction> = Object.fromEntries(
  directions.map((d) => [d.meta.id, d]),
);
