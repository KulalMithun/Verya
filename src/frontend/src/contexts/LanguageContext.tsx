import { i18n } from '@lingui/core';
import { I18nProvider } from '@lingui/react';
import { LoadingOverlay, Text } from '@mantine/core';
import { type JSX, useEffect, useRef, useState } from 'react';

import { useStoredTableState } from '@lib/states/StoredTableState';
import { useShallow } from 'zustand/react/shallow';
import { api } from '../App';
import { markLocaleReady } from '../functions/localeReady';
import { messages as defaultEnglishMessages } from '../locales/en/messages';
import { useLocalState } from '../states/LocalState';
import { useServerApiState } from '../states/ServerApiState';
import { fetchGlobalStates } from '../states/states';

export const defaultLocale = 'en';

// Immediately preload default English messages so all components render proper labels from frame 0
i18n.load('en', defaultEnglishMessages);
i18n.load('en-us', defaultEnglishMessages);
i18n.load('en_US', defaultEnglishMessages);
i18n.activate('en');

/*
 * Function which returns a record of supported languages.
 * Note that this is not a constant, as it is used in the LanguageSelect component
 */
export const getSupportedLanguages = (): Record<string, string> => {
  return {
    ar: 'العربية',
    bg: 'Български',
    cs: 'Čeština',
    da: 'Dansk',
    de: 'Deutsch',
    el: 'Ελληνικά',
    en: 'English',
    es: 'Español',
    es_MX: 'Español (México)',
    et: 'Eesti',
    fa: 'فارسی',
    fi: 'Suomi',
    fr: 'Français',
    he: 'עברית',
    hi: 'हिन्दी',
    hu: 'Magyar',
    it: 'Italiano',
    ja: '日本語',
    ko: '한국어',
    lt: 'Lietuvių',
    lv: 'Latviešu',
    nl: 'Nederlands',
    no: 'Norsk',
    pl: 'Polski',
    pt: 'Português',
    pt_BR: 'Português (Brasil)',
    ro: 'Română',
    ru: 'Русский',
    sk: 'Slovenčina',
    sl: 'Slovenščina',
    sr: 'Српски',
    sv: 'Svenska',
    th: 'ไทย',
    tr: 'Türkçe',
    uk: 'Українська',
    vi: 'Tiếng Việt',
    zh_Hans: '中文（简体）',
    zh_Hant: '中文（繁體）'
  };
};

export function LanguageContext({
  children
}: Readonly<{ children: JSX.Element }>) {
  const [language] = useLocalState(useShallow((state) => [state.language]));
  const [server] = useServerApiState(useShallow((state) => [state.server]));

  const [activeLocale, setActiveLocale] = useState<string | null>(null);

  useEffect(() => {
    // Update the locale based on prioritization:
    // 1. Locally selected locale
    // 2. Server default locale
    // 3. English (fallback)

    let locale: string | null = activeLocale;

    if (!!language) {
      locale = language;
    } else if (!!server.default_locale) {
      locale = server.default_locale;
    } else {
      locale = defaultLocale;
    }

    if (locale != activeLocale) {
      setActiveLocale(locale);
      activateLocale(locale);
    }
  }, [activeLocale, language, server.default_locale, defaultLocale]);

  const [loadedState, setLoadedState] = useState<
    'loading' | 'loaded' | 'error'
  >('loaded');
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;

    let lang: string = language || defaultLocale;

    // Ensure that the selected language is supported
    if (!Object.keys(getSupportedLanguages()).includes(lang)) {
      lang = defaultLocale;
    }

    activateLocale(lang)
      .then(() => {
        if (isMounted.current) setLoadedState('loaded');

        /*
         * Configure the default Accept-Language header for all requests.
         * - Locally selected locale
         * - Server default locale
         * - en-us (backup)
         */
        const locales: (string | undefined)[] = [];

        if (!!lang && lang != 'pseudo-LOCALE') {
          locales.push(lang);
        }

        if (!!server.default_locale) {
          locales.push(server.default_locale);
        }

        if (locales.indexOf('en-us') < 0) {
          locales.push('en-us');
        }

        // Ensure that the locales are properly formatted
        const new_locales = locales
          .map((locale) => locale?.replaceAll('_', '-').toLowerCase())
          .join(', ');

        if (new_locales == api.defaults.headers.common['Accept-Language']) {
          return;
        }

        // Update default Accept-Language headers
        api.defaults.headers.common['Accept-Language'] = new_locales;

        // Reload server state (and refresh status codes). Forced: the
        // Accept-Language header actually changed (initial set, or a real
        // locale change), so this must not be skipped by the "already
        // fetched" guard even if another caller already fetched once.
        fetchGlobalStates(true);

        // Clear out cached table column names
        useStoredTableState.getState().clearTableColumnNames();
      })
      /* istanbul ignore next */
      .catch((err) => {
        console.error('ERR: Failed loading translations', err);
        if (isMounted.current) setLoadedState('error');
      });

    return () => {
      isMounted.current = false;
    };
  }, [language]);

  return (
    <I18nProvider i18n={i18n} key={activeLocale || language || 'en'}>
      {children}
    </I18nProvider>
  );
}

// This function is used to determine the locale to activate based on the prioritization rules.
export function getPriorityLocale(): string {
  const serverDefault = useServerApiState.getState().server.default_locale;
  const userDefault = useLocalState.getState().language;

  return userDefault || serverDefault || defaultLocale;
}

const localeModules = import.meta.glob('../locales/*/messages.ts');

export async function activateLocale(locale: string | null) {
  if (!locale) {
    locale = getPriorityLocale();
  }

  // Ensure default English messages are always present in the dictionary
  if (!i18n.messages.en) {
    i18n.load('en', defaultEnglishMessages);
    i18n.load('en-us', defaultEnglishMessages);
    i18n.load('en_US', defaultEnglishMessages);
  }

  if (locale === 'en' || locale === 'en-us' || locale === 'en_US') {
    i18n.activate('en');
    markLocaleReady();
    return;
  }

  const localeDir = locale.split('-')[0];
  const targetPath = `../locales/${localeDir}/messages.ts`;
  const defaultPath = '../locales/en/messages.ts';

  try {
    const loader = localeModules[targetPath] || localeModules[defaultPath];
    if (loader) {
      const mod: any = await loader();
      const messages = mod.messages || mod.default || mod;
      i18n.load(locale, messages);
      i18n.activate(locale);
    } else {
      i18n.activate('en');
    }
  } catch (err) {
    console.warn(`Failed to load locale ${locale}, falling back to English:`, err);
    i18n.activate('en');
  } finally {
    markLocaleReady();
  }
}
