import { StylishText } from '@lib/components/StylishText';
import { Trans } from '@lingui/react/macro';
import {
  Button,
  Center,
  Container,
  Divider,
  Group,
  Loader,
  Paper,
  Stack,
  Text
} from '@mantine/core';
import { Outlet, useNavigate } from 'react-router-dom';
import SplashScreen from '../../components/SplashScreen';
import { doLogout } from '../../functions/auth';

export default function LoginLayoutComponent() {
  return (
    <SplashScreen>
      <Center mih='100vh' p='lg'>
        <Container>
          <Outlet />
        </Container>
      </Center>
    </SplashScreen>
  );
}

export function Wrapper({
  children,
  titleText,
  logOff = false,
  loader = false,
  smallPadding = false
}: Readonly<{
  children?: React.ReactNode;
  titleText: string;
  logOff?: boolean;
  loader?: boolean;
  smallPadding?: boolean;
}>) {
  const navigate = useNavigate();

  return (
    <Paper
      p='xl'
      withBorder
      miw={425}
      shadow='xl'
      style={{
        backgroundColor: 'rgba(26, 32, 53, 0.88)',
        backdropFilter: 'blur(16px)',
        borderColor: 'rgba(99, 102, 241, 0.3)',
        boxShadow:
          '0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 25px rgba(99, 102, 241, 0.15)',
        borderRadius: '12px'
      }}
    >
      <Stack gap={smallPadding ? 0 : 'md'}>
        <StylishText size='xl'>{titleText}</StylishText>
        {(titleText.includes('Veyra') || titleText.includes('OPENWES')) && (
          <Text size='xs' c='dimmed' mt={-4} mb={4}>
            Warehouse Execution System &bull; Powered by Veyra
          </Text>
        )}
        <Divider p='xs' />
        {loader && (
          <Group justify='center'>
            <Loader />
          </Group>
        )}
        {children}
        {logOff && (
          <>
            <Divider p='xs' />
            <Button onClick={() => doLogout(navigate)} color='red'>
              <Trans>Log off</Trans>
            </Button>
          </>
        )}
      </Stack>
    </Paper>
  );
}
