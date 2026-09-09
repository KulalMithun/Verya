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
  Modal,
  Paper,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Textarea,
  ThemeIcon,
  Title,
  Tooltip
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconBattery,
  IconBolt,
  IconCheck,
  IconClock,
  IconDeviceTablet,
  IconExclamationMark,
  IconEye,
  IconFlame,
  IconMapPin,
  IconPackage,
  IconPlayerPlay,
  IconRefresh,
  IconSearch,
  IconUser,
  IconUsers,
  IconWifi
} from '@tabler/icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApi } from '../../contexts/ApiContext';
import PageTitle from '../../components/nav/PageTitle';

export default function SupervisorBoard() {
  const api = useApi();
  const queryClient = useQueryClient();

  // Resolution modal state
  const [selectedException, setSelectedException] = useState<any>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [isResolving, setIsResolving] = useState(false);

  // Fetch Zones
  const { data: zonesData } = useQuery({
    queryKey: ['openwes-supervisor-zones'],
    queryFn: async () => {
      const res = await api.get('/api/openwes/zones/');
      return res.data?.results || res.data || [];
    }
  });

  // Fetch Operators
  const { data: operatorsData, refetch: refetchOperators } = useQuery({
    queryKey: ['openwes-supervisor-operators'],
    queryFn: async () => {
      const res = await api.get('/api/openwes/operators/');
      return res.data?.results || res.data || [];
    },
    refetchInterval: 8000
  });

  // Fetch Exceptions
  const { data: exceptionsData, refetch: refetchExceptions } = useQuery({
    queryKey: ['openwes-supervisor-exceptions'],
    queryFn: async () => {
      const res = await api.get('/api/openwes/exceptions/');
      return res.data?.results || res.data || [];
    },
    refetchInterval: 8000
  });

  // Fetch Real-time Audit Stream
  const { data: auditData } = useQuery({
    queryKey: ['openwes-supervisor-audit'],
    queryFn: async () => {
      const res = await api.get('/api/openwes/audit/', { params: { limit: 15 } });
      return res.data?.results || res.data || [];
    },
    refetchInterval: 5000
  });

  const zones = zonesData || [];
  const operators = operatorsData || [];
  const exceptions = exceptionsData || [];
  const auditLogs = auditData || [];

  const handleResolveException = async () => {
    if (!selectedException) return;
    setIsResolving(true);
    try {
      await api.post(`/api/openwes/exceptions/${selectedException.id}/resolve/`, {
        resolution: resolutionNotes || 'Investigated and resolved by supervisor.'
      });
      setSelectedException(null);
      setResolutionNotes('');
      queryClient.invalidateQueries({ queryKey: ['openwes-supervisor-exceptions'] });
      queryClient.invalidateQueries({ queryKey: ['openwes-dashboard'] });
    } catch (err: any) {
      alert(`Error resolving exception: ${err.message}`);
    } finally {
      setIsResolving(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PICKING':
        return 'indigo';
      case 'ONLINE':
      case 'IDLE':
        return 'teal';
      case 'BLOCKED':
        return 'red';
      case 'BREAK':
        return 'orange';
      default:
        return 'gray';
    }
  };

  return (
    <Container size="xl" py="lg">
      <PageTitle title="Veyra — Supervisor Operations Control" />

      {/* Header */}
      <Paper p="md" withBorder radius="sm" mb="lg">
        <Group justify="space-between">
          <div>
            <Group gap="xs">
              <ThemeIcon size="lg" color="indigo" variant="filled">
                <IconUsers size={20} />
              </ThemeIcon>
              <div>
                <Title order={2}>Supervisor Live Command Center</Title>
                <Text size="xs" c="dimmed">
                  Real-time floor monitoring, multi-zone visibility, active exceptions, and workforce state
                </Text>
              </div>
            </Group>
          </div>
          <Group gap="xs">
            <Button
              variant="default"
              size="xs"
              leftSection={<IconRefresh size={14} />}
              onClick={() => {
                refetchOperators();
                refetchExceptions();
              }}
            >
              Refresh Floor
            </Button>
            <Badge color="green" variant="dot" size="md">
              LIVE MONITORING
            </Badge>
          </Group>
        </Group>
      </Paper>

      {/* Zone Overview Grid */}
      <Title order={4} mb="xs" fw={700}>
        Warehouse Zone Real-time Heatmap
      </Title>
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md" mb="lg">
        {zones.map((zone: any) => {
          const zoneOps = operators.filter((o: any) => o.zone_code === zone.code);
          const hasBlocked = zoneOps.some((o: any) => o.status === 'BLOCKED');

          return (
            <Card key={zone.code} p="md" withBorder radius="sm" style={{ borderTop: `4px solid ${hasBlocked ? '#fa5252' : '#4c6ef5'}` }}>
              <Group justify="space-between" mb="xs">
                <div>
                  <Text fw={700} size="sm">
                    {zone.code}
                  </Text>
                  <Text size="xs" c="dimmed" lineClamp={1}>
                    {zone.name}
                  </Text>
                </div>
                <Badge size="xs" color={hasBlocked ? 'red' : 'indigo'} variant="light">
                  {zone.picking_strategy}
                </Badge>
              </Group>

              <Divider my="xs" />

              <Text size="xs" fw={600} mb={4} c="dimmed">
                Operators on Floor ({zoneOps.length}):
              </Text>
              <Stack gap={4}>
                {zoneOps.length > 0 ? (
                  zoneOps.map((op: any) => (
                    <Paper key={op.id} p={6} withBorder radius="xs" style={{ backgroundColor: op.status === 'BLOCKED' ? 'rgba(250, 82, 82, 0.1)' : undefined }}>
                      <Group justify="space-between">
                        <Group gap={6}>
                          <ThemeIcon size="xs" color={getStatusColor(op.status)} variant="filled" radius="xl">
                            <IconUser size={10} />
                          </ThemeIcon>
                          <Text size="xs" fw={600}>
                            {op.operator_username}
                          </Text>
                        </Group>
                        <Badge size="xs" color={getStatusColor(op.status)}>
                          {op.status}
                        </Badge>
                      </Group>
                      {op.current_task_id && (
                        <Text size="xs" c="dimmed" mt={2}>
                          Task: <b>{op.current_task_id}</b>
                        </Text>
                      )}
                    </Paper>
                  ))
                ) : (
                  <Text size="xs" c="dimmed" fs="italic">
                    No operators currently assigned in this zone.
                  </Text>
                )}
              </Stack>
            </Card>
          );
        })}
      </SimpleGrid>

      <Grid gap="md">
        {/* Left: Active Exceptions Management */}
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Paper p="md" withBorder radius="sm">
            <Group justify="space-between" mb="sm">
              <div>
                <Group gap="xs">
                  <Text fw={700} size="sm">
                    Active Warehouse Exceptions
                  </Text>
                  <Badge color="red" size="sm">
                    {exceptions.filter((e: any) => e.status !== 'RESOLVED').length} Open
                  </Badge>
                </Group>
                <Text size="xs" c="dimmed">
                  Tickets requiring supervisor investigation, stock count review, or relocation
                </Text>
              </div>
            </Group>

            <Table striped highlightOnHover withTableBorder withColumnBorders fz="xs">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Ticket</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Item / Loc</Table.Th>
                  <Table.Th>Operator</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {exceptions.map((ex: any) => (
                  <Table.Tr key={ex.id}>
                    <Table.Td fw={600}>{ex.exception_id}</Table.Td>
                    <Table.Td>
                      <Badge size="xs" color={ex.exception_type === 'SHORT_PICK' ? 'orange' : ex.exception_type === 'DAMAGED_ITEM' ? 'red' : 'yellow'}>
                        {ex.exception_type.replace('_', ' ')}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" fw={500} lineClamp={1}>
                        {ex.part_name || 'General Loc'}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {ex.location_name || 'Warehouse'}
                      </Text>
                    </Table.Td>
                    <Table.Td>{ex.operator_name}</Table.Td>
                    <Table.Td>
                      <Badge size="xs" color={ex.status === 'RESOLVED' ? 'green' : 'red'} variant="light">
                        {ex.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {ex.status !== 'RESOLVED' ? (
                        <Button
                          size="compact-xs"
                          color="indigo"
                          onClick={() => {
                            setSelectedException(ex);
                            setResolutionNotes('');
                          }}
                        >
                          Resolve
                        </Button>
                      ) : (
                        <Text size="xs" c="dimmed">
                          Resolved
                        </Text>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Paper>
        </Grid.Col>

        {/* Right: Live Warehouse Audit Event Stream */}
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Paper p="md" withBorder radius="sm">
            <Group justify="space-between" mb="xs">
              <Text fw={700} size="sm">
                Real-Time Warehouse Event Stream
              </Text>
              <Badge color="indigo" size="xs" variant="outline">
                AUDIT FEED
              </Badge>
            </Group>
            <Text size="xs" c="dimmed" mb="sm">
              Live immutable ledger of discrete operator actions and inventory deductions
            </Text>

            <Stack gap="xs" style={{ maxHeight: 420, overflowY: 'auto' }}>
              {auditLogs.map((log: any) => (
                <Paper key={log.id} p="xs" withBorder radius="xs" style={{ borderLeft: '3px solid #4c6ef5' }}>
                  <Group justify="space-between">
                    <Text size="xs" fw={600}>
                      {log.event_type.replace('_', ' ')}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </Text>
                  </Group>
                  <Text size="xs" c="dimmed" mt={2}>
                    {log.summary}
                  </Text>
                  <Group justify="space-between" mt={4}>
                    <Text size="xs" fw={500}>
                      Actor: {log.actor_name || 'System'}
                    </Text>
                    {log.task_id_str && (
                      <Badge size="xs" variant="subtle">
                        {log.task_id_str}
                      </Badge>
                    )}
                  </Group>
                </Paper>
              ))}
            </Stack>
          </Paper>
        </Grid.Col>
      </Grid>

      {/* Exception Resolution Modal */}
      <Modal
        opened={Boolean(selectedException)}
        onClose={() => setSelectedException(null)}
        title={`Resolve Exception: ${selectedException?.exception_id}`}
        centered
      >
        {selectedException && (
          <Stack gap="sm">
            <Paper p="xs" withBorder radius="xs" style={{ backgroundColor: '#1e293b' }}>
              <Text size="xs" c="dimmed">
                <b>Problem Description:</b>
              </Text>
              <Text size="sm" c="white" mt={2}>
                {selectedException.description}
              </Text>
              {selectedException.reported_quantity !== null && (
                <Text size="xs" c="orange.3" mt={4}>
                  Reported quantity available: {selectedException.reported_quantity} / {selectedException.expected_quantity}
                </Text>
              )}
            </Paper>

            <Textarea
              label="Supervisor Resolution Action / Notes"
              placeholder="e.g. Physical inventory counted. Replenishment triggered. Task unblocked."
              minRows={3}
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
            />

            <Group justify="flex-end" mt="xs">
              <Button variant="default" onClick={() => setSelectedException(null)}>
                Cancel
              </Button>
              <Button color="green" onClick={handleResolveException} loading={isResolving}>
                Confirm Resolution & Unblock Task
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
