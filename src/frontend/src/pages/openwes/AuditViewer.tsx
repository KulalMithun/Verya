import { useState } from 'react';
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  ThemeIcon,
  Title
} from '@mantine/core';
import {
  IconChecklist,
  IconEye,
  IconFilter,
  IconRefresh,
  IconSearch,
  IconShieldCheck
} from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import { useApi } from '../../contexts/ApiContext';
import PageTitle from '../../components/nav/PageTitle';

export default function AuditViewer() {
  const api = useApi();
  const [selectedLog, setSelectedLog] = useState<any>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState<string | null>(null);

  const { data: auditData, isLoading, refetch } = useQuery({
    queryKey: ['openwes-audit-events', eventTypeFilter],
    queryFn: async () => {
      const params: any = { ordering: '-timestamp', limit: 50 };
      if (eventTypeFilter) params.event_type = eventTypeFilter;
      const res = await api.get('/api/openwes/audit/', { params });
      return res.data?.results || res.data || [];
    }
  });

  const logs = auditData || [];

  return (
    <Container size="xl" py="lg">
      <PageTitle title="Veyra — Warehouse Audit Trail" />

      {/* Header */}
      <Paper p="md" withBorder radius="sm" mb="md">
        <Group justify="space-between">
          <div>
            <Group gap="xs">
              <ThemeIcon size="lg" color="indigo" variant="filled">
                <IconShieldCheck size={20} />
              </ThemeIcon>
              <div>
                <Title order={2}>Immutable Warehouse Audit Trail</Title>
                <Text size="xs" c="dimmed">
                  Complete compliance ledger tracking every scan, stock deduction, exception, and sync event
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
              Refresh Logs
            </Button>
          </Group>
        </Group>
      </Paper>

      {/* Filter Bar */}
      <Paper p="sm" withBorder radius="sm" mb="md">
        <Group justify="space-between">
          <Select
            placeholder="Filter Event Type"
            size="xs"
            clearable
            data={[
              { value: 'INVENTORY_ADJUSTED', label: 'Inventory Adjusted' },
              { value: 'TASK_COMPLETED', label: 'Task Completed' },
              { value: 'ITEM_SCANNED', label: 'Item Scanned' },
              { value: 'SHORT_PICK_REPORTED', label: 'Short Pick Reported' },
              { value: 'EXCEPTION_REPORTED', label: 'Exception Reported' },
              { value: 'EXCEPTION_RESOLVED', label: 'Exception Resolved' },
              { value: 'SYNC_COMPLETED', label: 'Offline Sync Completed' }
            ]}
            value={eventTypeFilter}
            onChange={setEventTypeFilter}
            style={{ width: 220 }}
          />

          <Text size="xs" c="dimmed">
            Showing latest <b>{logs.length}</b> verified events
          </Text>
        </Group>
      </Paper>

      {/* Logs Table */}
      <Paper withBorder radius="sm">
        <Table striped highlightOnHover withTableBorder withColumnBorders fz="xs">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Timestamp</Table.Th>
              <Table.Th>Event Type</Table.Th>
              <Table.Th>Actor</Table.Th>
              <Table.Th>Task ID</Table.Th>
              <Table.Th>Location</Table.Th>
              <Table.Th>Summary</Table.Th>
              <Table.Th>Details</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {logs.map((log: any) => (
              <Table.Tr key={log.id}>
                <Table.Td style={{ whiteSpace: 'nowrap' }}>
                  {new Date(log.timestamp).toLocaleString()}
                </Table.Td>
                <Table.Td>
                  <Badge size="xs" color="indigo" variant="outline">
                    {log.event_type}
                  </Badge>
                </Table.Td>
                <Table.Td fw={600}>{log.actor_name || 'System'}</Table.Td>
                <Table.Td>
                  {log.task_id_str ? (
                    <Text fw={600} style={{ fontFamily: 'monospace' }}>
                      {log.task_id_str}
                    </Text>
                  ) : (
                    '-'
                  )}
                </Table.Td>
                <Table.Td>{log.location_name || '-'}</Table.Td>
                <Table.Td>{log.summary}</Table.Td>
                <Table.Td>
                  <ActionIcon
                    size="sm"
                    variant="subtle"
                    color="indigo"
                    onClick={() => setSelectedLog(log)}
                  >
                    <IconEye size={14} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Paper>

      {/* Details JSON Modal */}
      <Modal
        opened={Boolean(selectedLog)}
        onClose={() => setSelectedLog(null)}
        title={`Audit Event: ${selectedLog?.event_type}`}
        centered
        size="lg"
      >
        {selectedLog && (
          <Stack gap="xs">
            <Text size="sm">
              <b>Summary:</b> {selectedLog.summary}
            </Text>
            <Text size="xs" c="dimmed">
              Actor: <b>{selectedLog.actor_name || 'System'}</b> | Time:{' '}
              {new Date(selectedLog.timestamp).toISOString()}
            </Text>
            <Paper
              p="sm"
              withBorder
              radius="xs"
              style={{ backgroundColor: '#1e293b', color: '#38d9a9', fontFamily: 'monospace' }}
            >
              <pre style={{ margin: 0, fontSize: '11px', overflowX: 'auto' }}>
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </Paper>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
