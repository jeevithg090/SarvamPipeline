import { useEffect, useState } from 'react';

const STORAGE_KEY = 'theme';
export const THEMES = ['system', 'light', 'dark'];

function readStoredTheme() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return THEMES.includes(value) ? value : 'system';
  } catch {
    return 'system';
  }
}

/**
 * Light / dark / system theme preference, applied as `data-theme` on <html>
 * and remembered in localStorage. index.html applies the stored value before
 * first paint to avoid a flash.
 */
export function useTheme() {
  const [theme, setTheme] = useState(readStoredTheme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'system') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // storage unavailable (private mode); the choice lasts for this visit
    }
  }, [theme]);

  return [theme, setTheme];
}
