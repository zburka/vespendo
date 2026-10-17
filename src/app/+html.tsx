import { ScrollViewStyleReset } from 'expo-router/html';
import type { PropsWithChildren } from 'react';

/** A webes (PWA) változat gyökér HTML-je: manifeszt, ikon és az iPhone "Főképernyőre" beállításai. */
export default function Root({ children }: PropsWithChildren) {
  return (
    <html lang="hu">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, shrink-to-fit=no, viewport-fit=cover"
        />
        <title>VeSpendo</title>
        <link rel="manifest" href="/manifest.webmanifest" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-title" content="VeSpendo" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="theme-color" content="#6750a4" />
        <meta name="color-scheme" content="light" />
        <style
          dangerouslySetInnerHTML={{
            __html: ':root{color-scheme:light}html,body{background-color:#fff;color:#1c1b1f}',
          }}
        />
        <ScrollViewStyleReset />
      </head>
      <body>{children}</body>
    </html>
  );
}
