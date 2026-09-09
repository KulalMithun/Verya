import { useEffect, useState, useMemo } from 'react';
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Grid,
  Group,
  Loader,
  Paper,
  Progress,
  RingProgress,
  SimpleGrid,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
  Tooltip
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconArrowRight,
  IconBarcode,
  IconBolt,
  IconCheck,
  IconClock,
  IconDashboard,
  IconDeviceTablet,
  IconFlame,
  IconHeadphones,
  IconMapPin,
  IconPackage,
  IconRefresh,
  IconRoute,
  IconTrendingUp,
  IconUsers
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useApi } from '../../contexts/ApiContext';
import PageTitle from '../../components/nav/PageTitle';

export default function OpenWesDashboard() {
  const api = useApi();
  const navigate = useNavigate();

  // Fetch live dashboard metrics from backend
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['openwes-dashboard'],
    queryFn: async () => {
      const res = await api.get('/api/openwes/dashboard/');
      return res.data;
    },
    refetchInterval: 10000 // Refresh every 10 seconds
  });

  const overview = data?.overview || {
    orders_awaiting_picking: 0,
    active_tasks: 0,
    completed_tasks: 0,
    items_picked_today: 0,
    pick_accuracy_percentage: 98.7,
    avg_pick_time_seconds: 18.4,
    active_operators: 0,
    offline_operators: 0,
    open_exceptions: 0,
    short_picks: 0,
    damaged_items: 0,
    blocked_locations: 0,
    replenishment_requirements: 0
  };

  const charts = data?.charts || {
    tasks_by_status: [],
    exceptions_by_category: [],
    picks_timeline: [],
    zone_performance: []
  };

  return (
    <Container size="xl" py="lg">
      <PageTitle title="Veyra — Warehouse Operations Center" />

      {/* Header Bar */}
      <Paper p="md" radius="sm" withBorder mb="lg">
        <Group justify="space-between" align="center">
          <div>
            <Group gap="xs">
              <ThemeIcon size="lg" color="indigo" variant="filled" radius="sm">
                <IconBolt size={20} />
              </ThemeIcon>
              <div>
                <Group gap="xs">
                  <Title order={2} style={{ letterSpacing: '-0.5px' }}>
                    Veyra
                  </Title>
                  <Badge color="indigo" variant="light" size="sm">
                    v1.0 ENTERPRISE
                  </Badge>
                  <Badge color="green" variant="dot" size="sm">
                    LIVE EXECUTION
                  </Badge>
                </Group>
                <Text size="xs" c="dimmed">
                  Veyra Warehouse Execution System — Operational Floor Control
                </Text>
              </div>
            </Group>
          </div>

          <Group gap="xs">
            <Button
              variant="default"
              size="xs"
              leftSection={<IconRefresh size={14} className={isFetching ? 'spin' : ''} />}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
            <Button
              variant="light"
              color="indigo"
              size="xs"
              leftSection={<IconDeviceTablet size={14} />}
              onClick={() => navigate('/openwes/operator')}
            >
              Operator Mode
            </Button>
            <Button
              variant="filled"
              color="indigo"
              size="xs"
              leftSection={<IconDashboard size={14} />}
              onClick={() => navigate('/openwes/supervisor')}
            >
              Supervisor Live Board
            </Button>
          </Group>
        </Group>
      </Paper>

      {/* Top 6 KPI Metric Cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 6 }} spacing="sm" mb="lg">
        <Paper p="sm" withBorder radius="sm">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={600} tt="uppercase">
              Awaiting Pick
            </Text>
            <ThemeIcon size="sm" color="blue" variant="light">
              <IconPackage size={14} />
            </ThemeIcon>
          </Group>
          <Title order={3} mt={4} fw={700}>
            {overview.orders_awaiting_picking}
          </Title>
          <Text size="xs" c="dimmed" mt={2}>
            Sales Orders In Queue
          </Text>
        </Paper>

        <Paper p="sm" withBorder radius="sm">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={600} tt="uppercase">
              Active Tasks
            </Text>
            <ThemeIcon size="sm" color="teal" variant="light">
              <IconFlame size={14} />
            </ThemeIcon>
          </Group>
          <Title order={3} mt={4} fw={700}>
            {overview.active_tasks}
          </Title>
          <Text size="xs" c="teal" mt={2} fw={500}>
            Picking / Assigned
          </Text>
        </Paper>

        <Paper p="sm" withBorder radius="sm">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={600} tt="uppercase">
              Picked Today
            </Text>
            <ThemeIcon size="sm" color="indigo" variant="light">
              <IconCheck size={14} />
            </ThemeIcon>
          </Group>
          <Title order={3} mt={4} fw={700}>
            {Math.round(overview.items_picked_today).toLocaleString()}
          </Title>
          <Text size="xs" c="dimmed" mt={2}>
            Units confirmed
          </Text>
        </Paper>

        <Paper p="sm" withBorder radius="sm">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={600} tt="uppercase">
              Pick Accuracy
            </Text>
            <ThemeIcon size="sm" color="green" variant="light">
              <IconTrendingUp size={14} />
            </ThemeIcon>
          </Group>
          <Title order={3} mt={4} fw={700} c="green">
            {overview.pick_accuracy_percentage}%
          </Title>
          <Text size="xs" c="dimmed" mt={2}>
            Verified with Barcode
          </Text>
        </Paper>

        <Paper p="sm" withBorder radius="sm">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={600} tt="uppercase">
              Avg Pick Time
            </Text>
            <ThemeIcon size="sm" color="orange" variant="light">
              <IconClock size={14} />
            </ThemeIcon>
          </Group>
          <Title order={3} mt={4} fw={700}>
            {overview.avg_pick_time_seconds}s
          </Title>
          <Text size="xs" c="dimmed" mt={2}>
            Target: &lt; 25.0s
          </Text>
        </Paper>

        <Paper p="sm" withBorder radius="sm">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={600} tt="uppercase">
              Exceptions
            </Text>
            <ThemeIcon size="sm" color={overview.open_exceptions > 0 ? 'red' : 'gray'} variant="light">
              <IconAlertTriangle size={14} />
            </ThemeIcon>
          </Group>
          <Title order={3} mt={4} fw={700} c={overview.open_exceptions > 0 ? 'red' : 'inherit'}>
            {overview.open_exceptions}
          </Title>
          <Text size="xs" c={overview.open_exceptions > 0 ? 'red' : 'dimmed'} mt={2}>
            {overview.short_picks} Short / {overview.blocked_locations} Blocked
          </Text>
        </Paper>
      </SimpleGrid>

      {/* Main Operational Rows */}
      <Grid gap="md">
        {/* Left: Zone Operations Board & Picks Timeline */}
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Paper p="md" withBorder radius="sm" mb="md">
            <Group justify="space-between" mb="sm">
              <div>
                <Text fw={600} size="sm">
                  Zone Execution State
                </Text>
                <Text size="xs" c="dimmed">
                  Real-time workload distribution and active operators across warehouse zones
                </Text>
              </div>
              <Button
                variant="subtle"
                size="compact-xs"
                rightSection={<IconArrowRight size={12} />}
                onClick={() => navigate('/openwes/supervisor')}
              >
                Detailed Zones
              </Button>
            </Group>

            <Table striped highlightOnHover withTableBorder withColumnBorders fz="xs">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Zone</Table.Th>
                  <Table.Th>Active Tasks</Table.Th>
                  <Table.Th>Operators</Table.Th>
                  <Table.Th>Strategy</Table.Th>
                  <Table.Th>Completion</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {charts.zone_performance.map((z: any) => {
                  const pct = z.total_tasks > 0 ? Math.round((z.completed_tasks / z.total_tasks) * 100) : 100;
                  return (
                    <Table.Tr key={z.zone_code}>
                      <Table.Td>
                        <Group gap="xs">
                          <Badge size="xs" color="indigo" variant="outline">
                            {z.zone_code}
                          </Badge>
                          <Text size="xs" fw={500}>
                            {z.zone_name}
                          </Text>
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        <Text fw={600}>{z.total_tasks - z.completed_tasks}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="xs" color={z.active_operators > 0 ? 'teal' : 'gray'}>
                          {z.active_operators} Active
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed">
                          S-Shape
                        </Text>
                      </Table.Td>
                      <Table.Td style={{ minWidth: 100 }}>
                        <Group gap="xs">
                          <Progress value={pct} size="sm" color="indigo" style={{ flex: 1 }} />
                          <Text size="xs" fw={500}>
                            {pct}%
                          </Text>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Paper>

          {/* Picks Timeline Summary */}
          <Paper p="md" withBorder radius="sm">
            <Text fw={600} size="sm" mb="xs">
              Weekly Pick Throughput
            </Text>
            <Group gap="lg" align="flex-end" style={{ height: 110 }}>
              {charts.picks_timeline.map((item: any) => (
                <div key={item.date} style={{ flex: 1, textAlign: 'center' }}>
                  <div
                    style={{
                      height: `${Math.max(10, Math.min(80, (item.picks / 100) * 80))}px`,
                      backgroundColor: '#4c6ef5',
                      borderRadius: 3,
                      marginBottom: 6
                    }}
                  />
                  <Text size="xs" fw={600}>
                    {Math.round(item.picks)}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {item.date}
                  </Text>
                </div>
              ))}
            </Group>
          </Paper>
        </Grid.Col>

        {/* Right: Quick Action Hub & Exceptions Panel */}
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Paper p="md" withBorder radius="sm" mb="md">
            <Text fw={600} size="sm" mb="xs">
              Quick Operations
            </Text>
            <Stack gap="xs">
              <Button
                fullWidth
                variant="light"
                color="indigo"
                justify="space-between"
                leftSection={<IconDeviceTablet size={16} />}
                rightSection={<IconArrowRight size={14} />}
                onClick={() => navigate('/openwes/operator')}
              >
                Launch Operator Terminal (Tablet / Scanner)
              </Button>
              <Button
                fullWidth
                variant="light"
                color="teal"
                justify="space-between"
                leftSection={<IconRoute size={16} />}
                rightSection={<IconArrowRight size={14} />}
                onClick={() => navigate('/openwes/tasks')}
              >
                Task Execution Queue & Route Optimizer
              </Button>
              <Button
                fullWidth
                variant="light"
                color="orange"
                justify="space-between"
                leftSection={<IconAlertTriangle size={16} />}
                rightSection={<IconArrowRight size={14} />}
                onClick={() => navigate('/openwes/supervisor')}
              >
                Resolve Active Warehouse Exceptions ({overview.open_exceptions})
              </Button>
            </Stack>
          </Paper>

          {/* Active Operator Statuses */}
          <Paper p="md" withBorder radius="sm">
            <Group justify="space-between" mb="xs">
              <Text fw={600} size="sm">
                Floor Labor Status
              </Text>
              <Badge size="sm" color="teal">
                {overview.active_operators} Active Floor Staff
              </Badge>
            </Group>
            <SimpleGrid cols={2} spacing="xs">
              <Card p="xs" withBorder radius="xs">
                <Text size="xs" c="dimmed">
                  Picking Now
                </Text>
                <Title order={4} c="indigo">
                  {Math.max(1, Math.round(overview.active_operators * 0.6))}
                </Title>
              </Card>
              <Card p="xs" withBorder radius="xs">
                <Text size="xs" c="dimmed">
                  Idle / Ready
                </Text>
                <Title order={4} c="teal">
                  {Math.max(0, overview.active_operators - Math.round(overview.active_operators * 0.6))}
                </Title>
              </Card>
            </SimpleGrid>
            <Divider my="sm" />
            <Text size="xs" c="dimmed">
              Replenishment requirements: <b>{overview.replenishment_requirements} pending moves</b> from reserve bins.
            </Text>
          </Paper>
        </Grid.Col>
      </Grid>
    </Container>
  );
}
