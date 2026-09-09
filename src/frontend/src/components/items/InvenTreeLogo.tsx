import { t } from '@lingui/core/macro';
import { ActionIcon } from '@mantine/core';
import { type ReactNode, forwardRef } from 'react';
import { NavLink } from 'react-router-dom';

import { useShallow } from 'zustand/react/shallow';
import { useServerApiState } from '../../states/ServerApiState';
import veyraIcon from '../../assets/veyra_icon.png';

export const InvenTreeLogoHomeButton = forwardRef<HTMLDivElement>(
  (props, ref) => {
    return (
      <div ref={ref} {...props}>
        <NavLink to={'/'}>
          <ActionIcon size={28} variant='transparent'>
            <InvenTreeLogo />
          </ActionIcon>
        </NavLink>
      </div>
    );
  }
);

/*
 * Render the Veyra logo
 * - Uses the custom logo if one is defined on the server
 * - Otherwise, uses the default Veyra logo
 */
export function InvenTreeLogo(): ReactNode {
  const [server] = useServerApiState(
    useShallow((state) => [state.server, state.fetchServerApiState])
  );

  if (server.server && server.customize?.logo) {
    return (
      <img src={server.customize.logo} alt={t`Veyra Logo`} height={28} />
    );
  }

  return <img src={veyraIcon} alt={t`Veyra Logo`} height={28} />;
}
