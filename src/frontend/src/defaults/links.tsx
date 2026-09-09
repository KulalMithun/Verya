import { t } from '@lingui/core/macro';
import { Trans } from '@lingui/react/macro';
import { openContextModal } from '@mantine/modals';

import { StylishText } from '@lib/components/StylishText';
import { UserRoles } from '@lib/enums/Roles';
import type { SettingsStateProps } from '@lib/types/Settings';
import type { UserStateProps } from '@lib/types/User';
import {
  IconBolt,
  IconBox,
  IconBuildingFactory2,
  IconBuildingWarehouse,
  IconDashboard,
  IconDeviceTablet,
  IconPackages,
  IconShoppingCart,
  IconTruckDelivery
} from '@tabler/icons-react';
import type { ReactNode } from 'react';
import type { MenuLinkItem } from '../components/items/MenuLinks';
import { useGlobalSettingsState } from '../states/SettingsStates';

type NavTab = {
  name: string;
  title: string;
  icon: ReactNode;
  visible?: boolean;
};

export function getNavTabs(user: UserStateProps): NavTab[] {
  const globalSettings = useGlobalSettingsState.getState();

  const navTabs: NavTab[] = [
    {
      name: 'openwes',
      title: 'Warehouse Execution',
      icon: <IconBuildingWarehouse />
    },
    {
      name: 'home',
      title: 'Core Dashboard',
      icon: <IconDashboard />
    },
    {
      name: 'part',
      title: t`Parts`,
      icon: <IconBox />,
      visible:
        user.hasViewRole(UserRoles.part) ||
        user.hasViewRole(UserRoles.part_category)
    },
    {
      name: 'stock',
      title: t`Stock`,
      icon: <IconPackages />,
      visible:
        user.hasViewRole(UserRoles.stock) ||
        user.hasViewRole(UserRoles.stock_location) ||
        (globalSettings.isSet('TRANSFERORDER_ENABLED') &&
          user.hasViewRole(UserRoles.transfer_order))
    },
    {
      name: 'manufacturing',
      title: t`Manufacturing`,
      icon: <IconBuildingFactory2 />,
      visible: user.hasViewRole(UserRoles.build)
    },
    {
      name: 'purchasing',
      title: t`Purchasing`,
      icon: <IconShoppingCart />,
      visible: user.hasViewRole(UserRoles.purchase_order)
    },
    {
      name: 'sales',
      title: t`Sales`,
      icon: <IconTruckDelivery />,
      visible:
        user.hasViewRole(UserRoles.sales_order) ||
        (globalSettings.isSet('RETURNORDER_ENABLED') &&
          user.hasViewRole(UserRoles.return_order))
    }
  ];

  return navTabs.filter((tab) => {
    return tab.visible !== false;
  });
}

export const docLinks = {
  docs: '/api-doc/',
  app: '/',
  getting_started: '/api-doc/',
  api: '/api-doc/',
  developer: '/api-doc/',
  faq: '/api-doc/',
  github: '',
  bug: '',
  releases: '',
  errorcodes: '/api-doc/'
};

export function DocumentationLinks(): MenuLinkItem[] {
  return [
    {
      id: 'api-docs',
      title: 'API Reference',
      link: '/api-doc/',
      external: true,
      description: 'Interactive OpenAPI and Swagger UI'
    },
    {
      id: 'redoc',
      title: 'Redoc API',
      link: '/api-doc/redoc/',
      external: true,
      description: 'Alternative Redoc API documentation'
    }
  ];
}

export function serverInfo() {
  return openContextModal({
    modal: 'info',
    title: (
      <StylishText size='xl'>
        <Trans>System Information</Trans>
      </StylishText>
    ),
    size: 'xl',
    innerProps: {}
  });
}

export function aboutInvenTree() {
  return openContextModal({
    modal: 'about',
    title: (
      <StylishText size='xl'>
        <Trans>About Veyra</Trans>
      </StylishText>
    ),
    size: 'xl',
    innerProps: {}
  });
}

export function licenseInfo() {
  return openContextModal({
    modal: 'license',
    title: (
      <StylishText size='xl'>
        <Trans>License Information</Trans>
      </StylishText>
    ),
    size: 'xl',
    innerProps: {}
  });
}

export function AboutLinks(
  settings: SettingsStateProps,
  user: UserStateProps
): MenuLinkItem[] {
  const base_items: MenuLinkItem[] = [
    {
      id: 'documentation',
      title: 'Documentation',
      description: 'Veyra API & System Documentation',
      link: '/api-doc/',
      external: true
    },
    {
      id: 'instance',
      title: 'System Information',
      description: 'About this Veyra instance',
      icon: 'info',
      action: serverInfo
    },
    {
      id: 'licenses',
      title: 'License Information',
      description: 'Licenses for third-party dependencies',
      icon: 'license',
      action: licenseInfo
    }
  ];

  // Restrict the about link if that setting is set
  if (user.isSuperuser() || !settings.isSet('INVENTREE_RESTRICT_ABOUT')) {
    base_items.push({
      id: 'about',
      title: 'About Veyra',
      description: 'About the Veyra Platform',
      icon: 'info',
      action: aboutInvenTree
    });
  }
  return base_items;
}
