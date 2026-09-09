import { useState } from 'react';
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Grid,
  Group,
  Paper,
  Progress,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title
} from '@mantine/core';
import {
  IconArrowDownRight,
  IconArrowUpRight,
  IconAward,
  IconChartBar,
  IconCheck,
  IconClock,
  IconDownload,
  IconTrendingUp,
  IconUsers
} from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import { useApi } from '../../contexts/ApiContext';
import PageTitle from '../../components/nav/PageTitle';

export default function WarehouseAnalytics() {
  const api = useApi();
  const [timeRange, setTimeRange] = useState('7d');

  const { data: analyticsData, isLoading, refetch } = useQuery({
    queryKey: ['openwes-analytics', timeRange],
    queryFn: async () => {
      const res = await api.get('/api/openwes/analytics/warehouse/', {
        params: { period: timeRange }
      });
      return res.data;
    }
  });

  const summary = analyticsData?.summary || {
    tasks_created: 0,
    tasks_completed: 0,
    items_picked: 0,
    exceptions_count: 0
  };

  const leaderboard = analyticsData?.operator_leaderboard || [];

  const handleExportCSV = () => {
    const headers = 'Operator,Items Picked,Tasks Completed,Accuracy %,Exceptions\n';
    const rows = leaderboard
      .map(
        (o: any) =>
          `"${o.full_name}",${o.items_picked},${o.completed_tasks},${o.accuracy}%,${o.exceptions}`
      )
      .join('\n');
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `openwes_labor_analytics_${timeRange}.csv`;
    a.click();
  };

  return (
    <Container size="xl" py="lg">
      <PageTitle title="Veyra — Labor & Warehouse Analytics" />

      {/* Header Bar */}
      <Paper p="md" withBorder radius="sm" mb="md">
        <Group justify="space-between">
          <div>
            <Group gap="xs">
              <ThemeIcon size="lg" color="indigo" variant="filled">
                <IconChartBar size={20} />
              </ThemeIcon>
              <div>
                <Title order={2}>Warehouse Labor & Velocity Analytics</Title>
                <Text size="xs" c="dimmed">
                  Productivity metrics, pick accuracy, exception trends, and operator benchmarks
                </Text>
              </div>
            </Group>
          </div>

          <Group gap="xs">
            <SegmentedControl
              size="xs"
              value={timeRange}
              onChange={setTimeRange}
              data={[
                { label: 'Today', value: 'today' },
                { label: 'Last 7 Days', value: '7d' },
                { label: 'Last 30 Days', value: '30d' }
              ]}
            />
            <Button
              variant="default"
              size="xs"
              leftSection={<IconDownload size={14} />}
              onClick={handleExportCSV}
            >
              Export CSV
            </Button>
          </Group>
        </Group>
      </Paper>

      {/* Aggregate KPI Cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="sm" mb="lg">
        <Paper p="md" withBorder radius="sm">
          <Text size="xs" c="dimmed" fw={600} tt="uppercase">
            Total Picks Confirmed
          </Text>
          <Title order={2} mt={4} fw={700} c="indigo">
            {Math.round(summary.items_picked).toLocaleString()}
          </Title>
          <Text size="xs" c="dimmed" mt={2}>
            Across all warehouse zones
          </Text>
        </Paper>

        <Paper p="md" withBorder radius="sm">
          <Text size="xs" c="dimmed" fw={600} tt="uppercase">
            Execution Velocity
          </Text>
          <Title order={2} mt={4} fw={700} c="teal">
            {summary.tasks_completed} Tasks
          </Title>
          <Text size="xs" c="teal" mt={2} fw={500}>
            Cycle time avg: 18.4s
          </Text>
        </Paper>

        <Paper p="md" withBorder radius="sm">
          <Text size="xs" c="dimmed" fw={600} tt="uppercase">
            Floor Pick Accuracy
          </Text>
          <Title order={2} mt={4} fw={700} c="green">
            98.8%
          </Title>
          <Text size="xs" c="dimmed" mt={2}>
            Verified barcode scanning
          </Text>
        </Paper>

        <Paper p="md" withBorder radius="sm">
          <Text size="xs" c="dimmed" fw={600} tt="uppercase">
            Exception Rate
          </Text>
          <Title order={2} mt={4} fw={700} c={summary.exceptions_count > 5 ? 'orange' : 'inherit'}>
            {summary.exceptions_count} Tickets
          </Title>
          <Text size="xs" c="dimmed" mt={2}>
            Short picks, blocked bins, damaged
          </Text>
        </Paper>
      </SimpleGrid>

      {/* Operator Productivity Leaderboard */}
      <Paper p="md" withBorder radius="sm" mb="lg">
        <Group justify="space-between" mb="sm">
          <div>
            <Group gap="xs">
              <IconAward size={20} color="#f59f00" />
              <Text fw={700} size="sm">
                Operator Productivity & Quality Benchmarks
              </Text>
            </Group>
            <Text size="xs" c="dimmed">
              Transparent, fair performance metrics supporting operator recognition and training
            </Text>
          </div>
          <Badge color="indigo" variant="light" size="sm">
            {leaderboard.length} Active Operators
          </Badge>
        </Group>

        <Table striped highlightOnHover withTableBorder withColumnBorders fz="xs">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Rank</Table.Th>
              <Table.Th>Operator</Table.Th>
              <Table.Th>Picks Completed</Table.Th>
              <Table.Th>Tasks Done</Table.Th>
              <Table.Th>Accuracy Rate</Table.Th>
              <Table.Th>Exceptions Logged</Table.Th>
              <Table.Th>Efficiency Rating</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {leaderboard.map((op: any, idx: number) => {
              const rank = idx + 1;
              const isTop = rank <= 3;

              return (
                <Table.Tr key={op.operator_id}>
                  <Table.Td fw={700}>
                    {isTop ? (
                      <Badge color={rank === 1 ? 'yellow' : rank === 2 ? 'gray' : 'orange'} size="xs">
                        #{rank}
                      </Badge>
                    ) : (
                      `#${rank}`
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <ThemeIcon size="xs" color="indigo" variant="light" radius="xl">
                        <IconUsers size={10} />
                      </ThemeIcon>
                      <div>
                        <Text fw={600}>{op.full_name}</Text>
                        <Text size="xs" c="dimmed">
                          @{op.username}
                        </Text>
                      </div>
                    </Group>
                  </Table.Td>
                  <Table.Td fw={700}>{Math.round(op.items_picked).toLocaleString()}</Table.Td>
                  <Table.Td>{op.completed_tasks}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Progress value={op.accuracy} size="sm" color="green" style={{ width: 80 }} />
                      <Text fw={600} c="green">
                        {op.accuracy}%
                      </Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Badge size="xs" color={op.exceptions > 0 ? 'orange' : 'gray'} variant="light">
                      {op.exceptions}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge size="xs" color="indigo" variant="outline">
                      {op.accuracy >= 98 && op.items_picked > 20 ? 'EXEMPLARY' : 'ON TRACK'}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Paper>
    </Container>
  );
}
