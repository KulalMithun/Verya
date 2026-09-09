import { useEffect, useState, useRef, useCallback } from 'react';
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Modal,
  NumberInput,
  Paper,
  Progress,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
  Tooltip
} from '@mantine/core';
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconArrowLeft,
  IconArrowRight,
  IconBarcode,
  IconCheck,
  IconCloudCheck,
  IconDeviceFloppy,
  IconExclamationMark,
  IconHelp,
  IconMapPin,
  IconMicrophone,
  IconMicrophoneOff,
  IconPackage,
  IconRefresh,
  IconVolume,
  IconWifi,
  IconWifiOff
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useApi } from '../../contexts/ApiContext';

export default function OperatorMode() {
  const api = useApi();
  const navigate = useNavigate();

  // Network online/offline state
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [offlineQueue, setOfflineQueue] = useState<any[]>(() => {
    try {
      const saved = localStorage.getItem('openwes_offline_queue');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Current active task and route sequence
  const [activeTaskIndex, setActiveTaskIndex] = useState<number>(() => {
    try {
      const savedIndex = localStorage.getItem('openwes_active_index');
      return savedIndex ? parseInt(savedIndex, 10) : 0;
    } catch {
      return 0;
    }
  });

  const [barcodeInput, setBarcodeInput] = useState('');
  const [barcodeValidation, setBarcodeValidation] = useState<'IDLE' | 'SUCCESS' | 'ERROR'>('IDLE');
  const [quantityPicked, setQuantityPicked] = useState<number>(0);

  // Voice Interaction State Machine
  const [voiceState, setVoiceState] = useState<string>('IDLE');
  const [isListening, setIsListening] = useState(false);
  const [lastUtterance, setLastUtterance] = useState('');
  const [voiceFeedback, setVoiceFeedback] = useState('Voice assistant ready. Say "Ready" to start.');
  const recognitionRef = useRef<any>(null);

  // Exception Modal
  const [exceptionModalOpen, setExceptionModalOpen] = useState(false);
  const [exceptionType, setExceptionType] = useState('SHORT_PICK');
  const [exceptionNotes, setExceptionNotes] = useState('');
  const [shortPickQty, setShortPickQty] = useState<number>(0);

  // Sync Status
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  // Fetch pending and assigned tasks
  const { data: tasksData, refetch: refetchTasks, isLoading } = useQuery({
    queryKey: ['openwes-operator-tasks'],
    queryFn: async () => {
      const res = await api.get('/api/openwes/tasks/', {
        params: {
          status: 'PENDING,ASSIGNED,IN_PROGRESS',
          ordering: 'sequence,priority'
        }
      });
      return res.data?.results || res.data || [];
    }
  });

  const tasks = tasksData || [];
  const currentTask = tasks[activeTaskIndex] || null;

  // Persist offline queue
  useEffect(() => {
    localStorage.setItem('openwes_offline_queue', JSON.stringify(offlineQueue));
  }, [offlineQueue]);

  // Persist session index for crash recovery
  useEffect(() => {
    localStorage.setItem('openwes_active_index', activeTaskIndex.toString());
  }, [activeTaskIndex]);

  // Monitor network status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      triggerSync();
    };
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [offlineQueue]);

  // Set initial picked quantity when current task changes
  useEffect(() => {
    if (currentTask) {
      setQuantityPicked(Number(currentTask.expected_quantity) || 1);
      setBarcodeValidation('IDLE');
      setBarcodeInput('');
    }
  }, [currentTask?.task_id]);

  // Text-To-Speech audio prompt
  const speakPrompt = useCallback((text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      window.speechSynthesis.speak(utterance);
    }
  }, []);

  // Web Speech API speech-to-text listener
  const startVoiceListener = useCallback(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setVoiceFeedback('Web Speech API not supported in this browser.');
      return;
    }

    if (recognitionRef.current) {
      recognitionRef.current.abort();
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      setVoiceFeedback('Listening for warehouse voice directive...');
    };

    recognition.onresult = async (event: any) => {
      const transcript = event.results[0][0].transcript;
      setLastUtterance(transcript);
      handleVoiceCommand(transcript);
    };

    recognition.onerror = (event: any) => {
      setIsListening(false);
      setVoiceFeedback(`Audio input error: ${event.error}`);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [currentTask, voiceState]);

  // Process spoken utterance through backend NLP and state machine
  const handleVoiceCommand = async (utterance: string) => {
    try {
      const res = await api.post('/api/openwes/voice/command/', {
        utterance,
        state: voiceState,
        task_id: currentTask?.task_id
      });

      const { result } = res.data;
      if (result) {
        setVoiceState(result.state);
        setVoiceFeedback(result.spoken_response);
        speakPrompt(result.spoken_response);

        // Execute task actions if FSM completed
        if (result.command === 'CONFIRM_PICK' || result.state === 'COMPLETED') {
          completeActiveTask(result.quantity || quantityPicked);
        } else if (result.command === 'SHORT_PICK') {
          handleShortPick(result.quantity || 1);
        } else if (result.command === 'BLOCKED_LOCATION') {
          handleReportException('BLOCKED_LOCATION', 'Location blocked by obstruction');
        }
      }
    } catch (err: any) {
      setVoiceFeedback(`Voice parsing error: ${err.message}`);
    }
  };

  // Barcode verification handler
  const handleBarcodeScan = (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentTask) return;

    const scanned = barcodeInput.trim().toUpperCase();
    const expectedSku = (currentTask.part_ipn || currentTask.part_name || '').toUpperCase();
    const barcodeMatch = (currentTask.part_name || '').toUpperCase();

    if (scanned === expectedSku || scanned === barcodeMatch || scanned.includes(expectedSku)) {
      setBarcodeValidation('SUCCESS');
      speakPrompt(`Item verified. Please confirm pick of ${currentTask.expected_quantity} units.`);
      setVoiceFeedback(`Item verified: ${currentTask.part_name}`);
      setVoiceState('AWAITING_QUANTITY');
    } else {
      setBarcodeValidation('ERROR');
      speakPrompt('Barcode mismatch. Please check SKU.');
      setVoiceFeedback(`Mismatch! Scanned ${scanned}, expected ${expectedSku}`);
    }
  };

  // Complete Active Task (Online or Offline Queue)
  const completeActiveTask = async (qty: number) => {
    if (!currentTask) return;

    const eventPayload = {
      event_id: crypto.randomUUID(),
      idempotency_key: `evt-pick-${currentTask.task_id}-${Date.now()}`,
      event_type: 'PICK_COMPLETED',
      payload: {
        task_id: currentTask.task_id,
        picked_quantity: qty,
        scanned_barcode: barcodeInput || currentTask.part_ipn
      },
      timestamp: new Date().toISOString()
    };

    if (!isOnline) {
      // Offline mode: store in local outbound queue
      setOfflineQueue((prev) => [...prev, eventPayload]);
      speakPrompt(`Offline pick recorded. ${qty} units queued for sync.`);
      setSyncNotice(`Task queued locally (Offline). Event ID: ${eventPayload.event_id.slice(0, 8)}...`);
      advanceToNextTask();
      return;
    }

    try {
      await api.post(`/api/openwes/tasks/${currentTask.id}/complete/`, {
        quantity: qty,
        scanned_barcode: barcodeInput || currentTask.part_ipn,
        validate_barcode: false
      });
      speakPrompt(`Confirmed. Pick completed.`);
      advanceToNextTask();
      refetchTasks();
    } catch (err: any) {
      // Network drop during call: fallback to offline queue
      setOfflineQueue((prev) => [...prev, eventPayload]);
      setSyncNotice('Network error: Action saved to offline queue.');
      advanceToNextTask();
    }
  };

  // Advance to next task in wave
  const advanceToNextTask = () => {
    if (activeTaskIndex < tasks.length - 1) {
      setActiveTaskIndex((prev) => prev + 1);
      setVoiceState('NAVIGATING');
    } else {
      speakPrompt('Picking wave completed. Great job!');
      setVoiceFeedback('All assigned tasks completed for this batch!');
    }
  };

  // Trigger Outbound Batch Sync
  const triggerSync = async () => {
    if (offlineQueue.length === 0 || isSyncing) return;
    setIsSyncing(true);

    try {
      const res = await api.post('/api/openwes/sync/', {
        events: offlineQueue,
        device_id: 'TABLET-OPERATOR-01'
      });

      const { synced_count, duplicate_count } = res.data;
      setSyncNotice(`Successfully synced ${synced_count} offline picks (${duplicate_count} duplicate reconciled).`);
      setOfflineQueue([]);
      refetchTasks();
    } catch (err: any) {
      setSyncNotice(`Sync retry failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  // Exception handling
  const handleReportException = async (type: string, description: string, reportedQty?: number) => {
    if (!currentTask) return;

    if (!isOnline) {
      const eventPayload = {
        event_id: crypto.randomUUID(),
        idempotency_key: `evt-ex-${currentTask.task_id}-${Date.now()}`,
        event_type: 'EXCEPTION_REPORTED',
        payload: {
          task_id: currentTask.task_id,
          exception_type: type,
          description,
          reported_quantity: reportedQty
        }
      };
      setOfflineQueue((prev) => [...prev, eventPayload]);
      advanceToNextTask();
      return;
    }

    try {
      await api.post(`/api/openwes/tasks/${currentTask.id}/exception/`, {
        exception_type: type,
        description,
        reported_quantity: reportedQty
      });
      setExceptionModalOpen(false);
      speakPrompt(`Exception recorded. Proceeding to next pick.`);
      advanceToNextTask();
      refetchTasks();
    } catch (err: any) {
      setVoiceFeedback(`Exception logging error: ${err.message}`);
    }
  };

  const handleShortPick = (qty: number) => {
    handleReportException(
      'SHORT_PICK',
      `Short pick: ${qty} of ${currentTask?.expected_quantity} available`,
      qty
    );
  };

  return (
    <Container size="sm" py="md" style={{ minHeight: '90vh' }}>
      {/* Top Status & Connectivity Bar */}
      <Paper p="xs" radius="sm" withBorder mb="sm">
        <Group justify="space-between">
          <Group gap="xs">
            <ActionIcon variant="subtle" color="gray" onClick={() => navigate('/openwes/dashboard')}>
              <IconArrowLeft size={18} />
            </ActionIcon>
            <div>
              <Text fw={700} size="sm">
                Veyra Terminal
              </Text>
              <Text size="xs" c="dimmed">
                Operator: Rajesh K. (Zone A)
              </Text>
            </div>
          </Group>

          <Group gap="xs">
            <Badge
              color={isOnline ? 'green' : 'red'}
              variant="light"
              size="sm"
              leftSection={isOnline ? <IconWifi size={12} /> : <IconWifiOff size={12} />}
            >
              {isOnline ? 'ONLINE' : 'OFFLINE MODE'}
            </Badge>
            {offlineQueue.length > 0 && (
              <Badge color="orange" variant="filled" size="sm">
                {offlineQueue.length} Queued
              </Badge>
            )}
            {offlineQueue.length > 0 && isOnline && (
              <Button size="compact-xs" color="indigo" onClick={triggerSync} loading={isSyncing}>
                Sync Now
              </Button>
            )}
          </Group>
        </Group>
      </Paper>

      {syncNotice && (
        <Alert
          icon={<IconCloudCheck size={16} />}
          color="teal"
          withCloseButton
          onClose={() => setSyncNotice(null)}
          mb="sm"
        >
          {syncNotice}
        </Alert>
      )}

      {/* Progress within Wave */}
      <Paper p="xs" withBorder radius="sm" mb="sm">
        <Group justify="space-between" mb={4}>
          <Text size="xs" fw={600} c="dimmed">
            WAVE EXECUTION PROGRESS
          </Text>
          <Text size="xs" fw={700}>
            Task {tasks.length > 0 ? activeTaskIndex + 1 : 0} of {tasks.length}
          </Text>
        </Group>
        <Progress
          value={tasks.length > 0 ? ((activeTaskIndex + 1) / tasks.length) * 100 : 0}
          size="sm"
          color="indigo"
          radius="xs"
        />
      </Paper>

      {/* Main Instruction Pick Card */}
      {currentTask ? (
        <Paper p="lg" radius="md" withBorder shadow="sm" mb="md" style={{ backgroundColor: '#182234', color: '#fff' }}>
          {/* Location Instruction */}
          <Stack gap="xs" align="center" ta="center">
            <Text size="xs" tt="uppercase" fw={700} c="indigo.2">
              PROCEED TO LOCATION
            </Text>
            <Paper
              p="sm"
              radius="sm"
              style={{
                backgroundColor: '#2b3a55',
                width: '100%',
                border: '2px solid #4c6ef5'
              }}
            >
              <Group justify="center" gap="xs">
                <IconMapPin size={24} color="#74c0fc" />
                <Title order={1} style={{ letterSpacing: '1px', color: '#ffffff' }}>
                  {currentTask.source_location_name || 'A-01-01'}
                </Title>
              </Group>
            </Paper>

            <Divider my="xs" color="#334155" style={{ width: '100%' }} />

            {/* SKU and Description */}
            <Text size="xs" c="gray.4" tt="uppercase" fw={600}>
              TARGET SKU / PART
            </Text>
            <Title order={2} style={{ color: '#fff' }}>
              {currentTask.part_name}
            </Title>
            <Badge size="md" color="indigo" variant="filled">
              SKU: {currentTask.part_ipn || 'NO-IPN'}
            </Badge>

            <Divider my="xs" color="#334155" style={{ width: '100%' }} />

            {/* Quantity */}
            <Text size="xs" c="yellow.3" tt="uppercase" fw={700}>
              PICK QUANTITY
            </Text>
            <Title order={1} style={{ fontSize: '2.5rem', color: '#ffd43b', lineHeight: 1 }}>
              {currentTask.expected_quantity} {currentTask.part_units || 'UNITS'}
            </Title>
          </Stack>
        </Paper>
      ) : (
        <Paper p="xl" withBorder radius="md" ta="center" mb="md">
          <ThemeIcon size="xl" color="green" radius="xl" variant="light" mb="md">
            <IconCheck size={32} />
          </ThemeIcon>
          <Title order={3}>All Tasks Completed</Title>
          <Text size="sm" c="dimmed" mt="xs">
            No remaining picks assigned to your session in this wave.
          </Text>
          <Button mt="md" variant="light" color="indigo" onClick={() => navigate('/openwes/dashboard')}>
            Return to Dashboard
          </Button>
        </Paper>
      )}

      {/* Barcode Validation Form */}
      {currentTask && (
        <Paper p="md" radius="sm" withBorder mb="md">
          <form onSubmit={handleBarcodeScan}>
            <Stack gap="xs">
              <Group justify="space-between">
                <Text size="xs" fw={700} tt="uppercase">
                  Barcode Validation
                </Text>
                {barcodeValidation === 'SUCCESS' && (
                  <Badge color="green" size="sm" leftSection={<IconCheck size={12} />}>
                    SKU VERIFIED
                  </Badge>
                )}
                {barcodeValidation === 'ERROR' && (
                  <Badge color="red" size="sm" leftSection={<IconAlertCircle size={12} />}>
                    INVALID BARCODE
                  </Badge>
                )}
              </Group>

              <Group gap="xs">
                <TextInput
                  placeholder="Scan or enter item barcode..."
                  leftSection={<IconBarcode size={16} />}
                  value={barcodeInput}
                  onChange={(e) => setBarcodeInput(e.target.value)}
                  style={{ flex: 1 }}
                  autoFocus
                />
                <Button type="submit" variant="filled" color="indigo">
                  Verify
                </Button>
              </Group>

              <Group justify="space-between" mt="xs">
                <Button
                  size="xs"
                  variant="subtle"
                  color="gray"
                  onClick={() => setBarcodeInput(currentTask.part_ipn || currentTask.part_name)}
                >
                  Quick Fill Barcode (Simulate Scan)
                </Button>
              </Group>
            </Stack>
          </form>
        </Paper>
      )}

      {/* Voice Assistant HUD & Controls */}
      <Paper p="md" radius="sm" withBorder mb="md" style={{ backgroundColor: '#101726', color: '#fff' }}>
        <Group justify="space-between" mb="xs">
          <Group gap="xs">
            <ThemeIcon color={isListening ? 'red' : 'indigo'} variant="filled" size="sm">
              <IconMicrophone size={14} />
            </ThemeIcon>
            <Text size="xs" fw={700} tt="uppercase" c="indigo.2">
              Voice-Directed Workflow
            </Text>
          </Group>
          <Badge size="xs" color="gray" variant="outline">
            FSM: {voiceState}
          </Badge>
        </Group>

        <Paper p="xs" radius="xs" style={{ backgroundColor: '#1e293b', minHeight: 48 }} mb="xs">
          <Text size="xs" c={isListening ? 'orange.2' : 'gray.3'}>
            <b>System:</b> {voiceFeedback}
          </Text>
          {lastUtterance && (
            <Text size="xs" c="blue.3" mt={2}>
              <b>You said:</b> "{lastUtterance}"
            </Text>
          )}
        </Paper>

        <Group justify="space-between">
          <Button
            size="sm"
            color={isListening ? 'red' : 'indigo'}
            leftSection={isListening ? <IconMicrophoneOff size={16} /> : <IconMicrophone size={16} />}
            onClick={startVoiceListener}
          >
            {isListening ? 'Listening...' : 'Push to Talk'}
          </Button>

          <Button
            size="sm"
            variant="default"
            leftSection={<IconVolume size={16} />}
            onClick={() => speakPrompt(voiceFeedback)}
          >
            Repeat Audio
          </Button>
        </Group>
      </Paper>

      {/* Action Buttons: Confirm Pick vs Exception */}
      {currentTask && (
        <Group grow mb="lg">
          <Button
            size="lg"
            color="green"
            leftSection={<IconCheck size={20} />}
            onClick={() => completeActiveTask(quantityPicked)}
          >
            Confirm Pick ({currentTask.expected_quantity})
          </Button>

          <Button
            size="lg"
            variant="outline"
            color="red"
            leftSection={<IconAlertTriangle size={18} />}
            onClick={() => setExceptionModalOpen(true)}
          >
            Report Exception
          </Button>
        </Group>
      )}

      {/* Exception Reporting Modal */}
      <Modal
        opened={exceptionModalOpen}
        onClose={() => setExceptionModalOpen(false)}
        title="Report Warehouse Exception"
        centered
        size="md"
      >
        <Stack gap="sm">
          <Text size="xs" c="dimmed">
            Reporting an exception will pause this task, flag the incident for the supervisor, and allow you to continue.
          </Text>

          <Button
            variant="light"
            color="orange"
            justify="flex-start"
            leftSection={<IconAlertTriangle size={16} />}
            onClick={() => {
              const qty = Math.max(0, Number(currentTask?.expected_quantity || 1) - 1);
              handleShortPick(qty);
            }}
          >
            Short Pick (Partial stock available in bin)
          </Button>

          <Button
            variant="light"
            color="red"
            justify="flex-start"
            leftSection={<IconExclamationMark size={16} />}
            onClick={() => handleReportException('DAMAGED_ITEM', 'Damaged merchandise found in bin')}
          >
            Damaged Item (Goods unusable / broken)
          </Button>

          <Button
            variant="light"
            color="yellow"
            justify="flex-start"
            leftSection={<IconMapPin size={16} />}
            onClick={() => handleReportException('BLOCKED_LOCATION', 'Aisle or bin physically blocked')}
          >
            Blocked Location (Forklift / obstruction blocking access)
          </Button>

          <Button
            variant="light"
            color="gray"
            justify="flex-start"
            leftSection={<IconPackage size={16} />}
            onClick={() => handleReportException('MISSING_ITEM', 'Bin is completely empty / missing')}
          >
            Missing Item (Zero stock found at location)
          </Button>
        </Stack>
      </Modal>
    </Container>
  );
}
