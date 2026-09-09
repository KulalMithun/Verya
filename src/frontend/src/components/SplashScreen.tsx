import { Box } from '@mantine/core';
import { useEffect } from 'react';
import { useShallow } from 'zustand/react/shallow';
import loginBg from '../assets/login_bg.png';
import { generateUrl } from '../functions/urls';
import { useServerApiState } from '../states/ServerApiState';
import { useUserState } from '../states/UserState';

/**
 * Render content within a "splash screen" container with blurred backdrop.
 */
export default function SplashScreen({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [server, fetchServerApiState] = useServerApiState(
    useShallow((state) => [state.server, state.fetchServerApiState])
  );
  const [checked_login] = useUserState(
    useShallow((state) => [state.login_checked])
  );

  // Fetch server data on mount if no server data is present
  useEffect(() => {
    if (server.server === null) {
      fetchServerApiState();
    }
  }, [server]);

  const bgImage =
    server.customize?.splash && checked_login
      ? generateUrl(server.customize.splash)
      : loginBg;

  return (
    <Box
      style={{
        position: 'relative',
        minHeight: '100vh',
        width: '100%',
        overflow: 'hidden',
        backgroundColor: '#070b19'
      }}
    >
      {/* Blurred background image layer */}
      <Box
        style={{
          position: 'fixed',
          inset: '-20px',
          backgroundImage: `url(${bgImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'blur(10px) brightness(0.8)',
          transform: 'scale(1.06)',
          zIndex: 0,
          pointerEvents: 'none'
        }}
      />
      {/* High-tech gradient overlay to enrich contrast and colors */}
      <Box
        style={{
          position: 'fixed',
          inset: 0,
          background:
            'radial-gradient(ellipse at center, rgba(13, 22, 48, 0.4) 0%, rgba(5, 8, 20, 0.75) 100%)',
          zIndex: 1,
          pointerEvents: 'none'
        }}
      />
      {/* Foreground content */}
      <Box
        style={{
          position: 'relative',
          zIndex: 2,
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
