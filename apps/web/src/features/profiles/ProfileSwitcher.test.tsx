import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ProfileSwitcher } from './ProfileSwitcher';

vi.mock('./ProfileContext', () => ({
  useCurrentProfile: () => ({
    profiles: [
      { id: 1, name: 'Personal', base_currency: 'CAD', is_archived: false },
      { id: 2, name: 'Household', base_currency: 'CAD', is_archived: false },
    ],
    currentProfile: { id: 1, name: 'Personal', base_currency: 'CAD', is_archived: false },
    currentProfileId: 1,
    selectProfile: vi.fn(),
    isLoading: false,
  }),
}));

describe('ProfileSwitcher', () => {
  it('uses a keyboard-friendly disclosure and restores focus on Escape', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><ProfileSwitcher /></MemoryRouter>);

    const trigger = screen.getByRole('button', { name: /Personal/ });
    await user.click(trigger);

    const choices = screen.getByRole('group', { name: 'Choose a profile' });
    const firstProfile = within(choices).getByRole('button', { name: /Personal/ });
    expect(firstProfile).toHaveFocus();
    expect(trigger).toHaveAttribute('aria-expanded', 'true');

    await user.tab();
    expect(within(choices).getByRole('button', { name: /Household/ })).toHaveFocus();

    await user.keyboard('{Escape}');
    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute('aria-expanded', 'false');

    await user.click(trigger);
    await user.click(within(screen.getByRole('group', { name: 'Choose a profile' })).getByRole('button', { name: /Household/ }));
    expect(trigger).toHaveFocus();

    await user.click(trigger);
    await user.click(screen.getByRole('button', { name: 'Close profile choices' }));
    expect(trigger).toHaveFocus();
  });
});
