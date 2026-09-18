import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../StatusBadge';

describe('StatusBadge', () => {
  it('renders AVAILABLE with emerald styling', () => {
    render(<StatusBadge status="AVAILABLE" />);
    const badge = screen.getByText('AVAILABLE');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('text-emerald-300');
  });

  it('renders RESTRICTED with amber styling', () => {
    render(<StatusBadge status="RESTRICTED" />);
    const badge = screen.getByText('RESTRICTED');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('text-amber-300');
  });

  it('renders INACCESSIBLE with rose styling', () => {
    render(<StatusBadge status="INACCESSIBLE" />);
    const badge = screen.getByText('INACCESSIBLE');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('text-rose-300');
  });

  it('renders IN_TRANSIT with cyan styling', () => {
    render(<StatusBadge status="IN_TRANSIT" />);
    const badge = screen.getByText('IN_TRANSIT');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('text-cyan-300');
  });
});
