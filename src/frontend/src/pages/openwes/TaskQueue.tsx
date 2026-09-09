import { useState } from 'react';
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Drawer,
  Group,
  Modal,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  ThemeIcon,
  Title,
  Tooltip
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconArrowRight,
  IconBarcode,
  IconCheck,
  IconFilter,
  IconPackage,
  IconPlayerPlay,
  IconRefresh,
  IconRoute,
  IconSearch,
  IconUserCheck,
  IconUserX,
  IconUsers
} from '@tabler/icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApi } from '../../contexts/ApiContext';
import PageTitle from '../../components/nav/PageTitle';

export default function TaskQueue() {
  const api = useApi();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [optimizedRoute, setOptimizedRoute] = useState<any[] | null>(null);
  const [routeDrawerOpen, setRouteDrawerOpen] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isAutoAssigning, setIsAutoAssigning] = useState(false);

  // Fetch Tasks
  const { data: tasksData, isLoading, refetch } = useQuery({
    queryKey: ['openwes-tasks', statusFilter, searchQuery],
    queryFn: async () => {
      const params: any = { ordering: 'sequence,-priority' };
      if (statusFilter) params.status = statusFilter;
      if (searchQuery) params.search = searchQuery;
      const res = await api.get('/api/openwes/tasks/', { params });
      return res.data?.results || res.data || [];
    }
  });

  const tasks = tasksData || [];

  // Run Route Optimization
  const handleOptimizeRoute = async (strategy: string = 'S_SHAPE') => {
    setIsOptimizing(true);
    try {
      const res = await api.post('/api/openwes/tasks/optimize-route/', {
        strategy
      });
      setOptimizedRoute(res.data.route);
      setRouteDrawerOpen(true);
      queryClient.invalidateQueries({ queryKey: ['openwes-tasks'] });
    } catch (err: any) {
      alert(`Optimization error: ${err.message}`);
    } finally {
      setIsOptimizing(false);
    }
  };

  // Run Auto-Assignment
  const handleAutoAssign = async () => {
    setIsAutoAssigning(true);
    try {
      const res = await api.post('/api/openwes/tasks/auto-assign/');
      alert(`Auto-assigned ${res.data.assigned_count} pending tasks to optimal operators.`);
      refetch();
    } catch (err: any) {
      alert(`Auto-assign error: ${err.message}`);
    } finally {
      setIsAutoAssigning(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <Badge color="green" size="xs">COMPLETED</Badge>;
      case 'IN_PROGRESS':
        return <Badge color="indigo" size="xs">IN PROGRESS</Badge>;
      case 'ASSIGNED':
        return <Badge color="teal" size="xs">ASSIGNED</Badge>;
      case 'PENDING':
        return <Badge color="gray" size="xs">PENDING</Badge>;
      case 'EXCEPTION':
        return <Badge color="red" size="xs">EXCEPTION</Badge>;
      case 'PAUSED':
        return <Badge color="yellow" size="xs">PAUSED</Badge>;
      case 'PARTIAL':
        return <Badge color="orange" size="xs">PARTIAL</Badge>;
      default:
        return <Badge color="gray" size="xs">{status}</Badge>;
    }
  };

  const getPriorityBadge = (priority: number) => {
    if (priority >= 40) return <Badge color="red" variant="dot" size="xs">CRITICAL</Badge>;
    if (priority >= 30) return <Badge color="orange" variant="dot" size="xs">HIGH</Badge>;
    if (priority >= 20) return <Badge color="blue" variant="dot" size="xs">MEDIUM</Badge>;
    return <Badge color="gray" variant="dot" size="xs">LOW</Badge>;
  };

  return (
    <Container size="xl" py="lg">
      <PageTitle title="Veyra — Warehouse Task Execution Queue" />

      {/* Header Bar */}
      <Paper p="md" withBorder radius="sm" mb="md">
        <Group justify="space-between">
          <div>
            <Group gap="xs">
              <ThemeIcon size="lg" color="indigo" variant="filled">
                <IconPackage size={20} />
              </ThemeIcon>
              <div>
                <Title order={2}>Warehouse Execution Task Queue</Title>
                <Text size="xs" c="dimmed">
                  Manage pick, putaway, replenishment, and cycle count execution orders
                </Text>
              </div>
            </Group>
          </div>

          <Group gap="xs">
            <Button
              variant="default"
              size="xs"
              leftSection={<IconRefresh size={14} />}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
            <Button
              variant="light"
              color="teal"
              size="xs"
              leftSection={<IconUserCheck size={14} />}
              onClick={handleAutoAssign}
              loading={isAutoAssigning}
            >
              Auto-Assign Queue
            </Button>
            <Button
              variant="filled"
              color="indigo"
              size="xs"
              leftSection={<IconRoute size={14} />}
              onClick={() => handleOptimizeRoute('S_SHAPE')}
              loading={isOptimizing}
            >
              Optimize Pick-Path (S-Shape)
            </Button>
          </Group>
        </Group>
      </Paper>

      {/* Filters Bar */}
      <Paper p="sm" withBorder radius="sm" mb="md">
        <Group justify="space-between">
          <Group gap="sm" style={{ flex: 1 }}>
            <TextInput
              placeholder="Search Task ID, SKU, location..."
              leftSection={<IconSearch size={14} />}
              size="xs"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: 280 }}
            />
            <Select
              placeholder="Filter by Status"
              size="xs"
              clearable
              data={[
                { value: 'PENDING', label: 'Pending' },
                { value: 'ASSIGNED', label: 'Assigned' },
                { value: 'IN_PROGRESS', label: 'In Progress' },
                { value: 'COMPLETED', label: 'Completed' },
                { value: 'EXCEPTION', label: 'Exception' }
              ]}
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 160 }}
            />
          </Group>
          <Text size="xs" c="dimmed">
            Showing <b>{tasks.length}</b> tasks
          </Text>
        </Group>
      </Paper>

      {/* Tasks Table */}
      <Paper withBorder radius="sm">
        <Table striped highlightOnHover withTableBorder withColumnBorders fz="xs">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Seq</Table.Th>
              <Table.Th>Task ID</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Priority</Table.Th>
              <Table.Th>Location</Table.Th>
              <Table.Th>SKU / Part Name</Table.Th>
              <Table.Th>Quantity</Table.Th>
              <Table.Th>Operator</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Order</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {tasks.map((task: any) => (
              <Table.Tr key={task.id}>
                <Table.Td fw={700}>#{task.sequence}</Table.Td>
                <Table.Td fw={600} style={{ fontFamily: 'monospace' }}>
                  {task.task_id}
                </Table.Td>
                <Table.Td>
                  <Badge size="xs" variant="outline" color="indigo">
                    {task.task_type}
                  </Badge>
                </Table.Td>
                <Table.Td>{getPriorityBadge(task.priority)}</Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    <IconPackage size={12} color="#74c0fc" />
                    <Text fw={600}>{task.source_location_name || 'N/A'}</Text>
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Text fw={500} lineClamp={1}>
                    {task.part_name}
                  </Text>
                  <Text size="xs" c="dimmed" style={{ fontFamily: 'monospace' }}>
                    {task.part_ipn}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text fw={600}>
                    {task.picked_quantity} / {task.expected_quantity}
                  </Text>
                </Table.Td>
                <Table.Td>
                  {task.operator_name ? (
                    <Badge size="xs" color="teal" variant="light">
                      {task.operator_name}
                    </Badge>
                  ) : (
                    <Text size="xs" c="dimmed">
                      Unassigned
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>{getStatusBadge(task.status)}</Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {task.order_reference || 'Ad-Hoc'}
                  </Text>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      {/* Pick Path Optimizer Drawer */}
      <Drawer
        opened={routeDrawerOpen}
        onClose={() => setRouteDrawerOpen(false)}
        title="Optimized Pick-Path Route Plan"
        position="right"
        size="lg"
      >
        {optimizedRoute && (
          <Stack gap="sm">
            <Alert color="indigo">
              Deterministic route sequence calculated using <b>S-Shape Warehouse Aisle Heuristic</b>. Sequential
              pick stops minimized backtracking across aisle bays.
            </Alert>

            <Table fz="xs" withTableBorder striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Step</Table.Th>
                  <Table.Th>Bin Location</Table.Th>
                  <Table.Th>SKU</Table.Th>
                  <Table.Th>Segment Dist</Table.Th>
                  <Table.Th>Total Dist</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {optimizedRoute.map((stop: any) => (
                  <Table.Tr key={stop.task_id}>
                    <Table.Td fw={700}>#{stop.sequence}</Table.Td>
                    <Table.Td fw={600}>{stop.location_name}</Table.Td>
                    <Table.Td>
                      <Text size="xs" lineClamp={1}>
                        {stop.part_name}
                      </Text>
                    </Table.Td>
                    <Table.Td>{stop.segment_distance}m</Table.Td>
                    <Table.Td fw={600} c="indigo">
                      {stop.cumulative_distance}m
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Stack>
        )}
      </Drawer>
    </Container>
  );
}
