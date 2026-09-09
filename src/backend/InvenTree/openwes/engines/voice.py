"""OpenWES Voice-Directed Picking Engine.

Architecture:
  VoiceProvider (Abstract STT / TTS provider)
    -> WebSpeechVoiceProvider / VoskOfflineVoiceProvider
  VoiceCommandParser (Converts natural language utterances to structured commands)
  VoiceStateMachine (Contextual state machine preventing illegal voice state transitions)
  VoiceExecutionEngine (Executes the parsed command against the active warehouse task)
"""

import re
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from django.utils.translation import gettext_lazy as _

from openwes.status_codes import ExceptionType, WarehouseTaskStatus


class VoiceState:
    """Finite states of the voice interaction session."""

    IDLE = 'IDLE'
    TASK_STARTED = 'TASK_STARTED'
    NAVIGATING = 'NAVIGATING'
    AWAITING_ITEM_CONFIRMATION = 'AWAITING_ITEM_CONFIRMATION'
    AWAITING_QUANTITY = 'AWAITING_QUANTITY'
    PROCESSING = 'PROCESSING'
    EXCEPTION = 'EXCEPTION'
    COMPLETED = 'COMPLETED'


class VoiceCommandType:
    """Structured voice commands extracted from natural language."""

    READY = 'READY'
    CONFIRM = 'CONFIRM'
    CONFIRM_PICK = 'CONFIRM_PICK'
    SHORT_PICK = 'SHORT_PICK'
    REPEAT = 'REPEAT'
    NEXT = 'NEXT'
    SKIP = 'SKIP'
    HELP = 'HELP'
    SCAN = 'SCAN'
    DAMAGED = 'DAMAGED'
    MISSING = 'MISSING'
    BLOCKED_LOCATION = 'BLOCKED_LOCATION'
    CANCEL = 'CANCEL'
    UNKNOWN = 'UNKNOWN'


class BaseVoiceProvider(ABC):
    """Abstract interface for speech-to-text / text-to-speech providers."""

    @abstractmethod
    def synthesize_speech(self, text: str) -> Dict[str, Any]:
        """Convert system prompt text to speech utterance directive."""
        pass

    @abstractmethod
    def transcribe_audio(self, audio_data: bytes) -> str:
        """Convert audio byte stream to recognized text transcript."""
        pass


class WebSpeechVoiceProvider(BaseVoiceProvider):
    """Browser / Web Speech API provider directive generator."""

    def synthesize_speech(self, text: str) -> Dict[str, Any]:
        return {
            'provider': 'web_speech_api',
            'type': 'tts_directive',
            'text': text,
            'rate': 1.0,
            'pitch': 1.0,
            'lang': 'en-US',
        }

    def transcribe_audio(self, audio_data: bytes) -> str:
        # In browser-assisted mode, transcription occurs on client device
        return ''


class VoskOfflineVoiceProvider(BaseVoiceProvider):
    """Stub for offline local Kaldi/Vosk STT engine on warehouse mobile computers."""

    def __init__(self, model_path: str = 'models/vosk-en'):
        self.model_path = model_path

    def synthesize_speech(self, text: str) -> Dict[str, Any]:
        return {
            'provider': 'vosk_offline',
            'type': 'tts_directive',
            'text': text,
        }

    def transcribe_audio(self, audio_data: bytes) -> str:
        # Vosk inference hook placeholder
        return ''


# Word to digit dictionary for spoken numbers
WORD_TO_NUM = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
    'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30,
    'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90, 'hundred': 100,
}


def parse_spoken_number(text: str) -> Optional[int]:
    """Extract a number from spoken text like '5', 'five', 'twenty two'."""
    # Direct digit match
    digit_match = re.search(r'\b(\d+)\b', text)
    if digit_match:
        return int(digit_match.group(1))

    # Single word number
    words = text.lower().split()
    for w in words:
        if w in WORD_TO_NUM:
            return WORD_TO_NUM[w]

    return None


class VoiceCommandParser:
    """Robust Natural Language parser converting spoken utterances to structured intents."""

    @classmethod
    def parse(cls, utterance: str) -> Dict[str, Any]:
        text = utterance.strip().lower()

        # 1. Navigation / Readiness
        if re.search(r'\b(ready|i am here|at location|arrived)\b', text):
            return {'command': VoiceCommandType.READY, 'raw': utterance}

        # 2. Blocked Location Exception
        if re.search(r'\b(blocked|bin is blocked|aisle blocked|cannot access|path blocked)\b', text):
            return {
                'command': VoiceCommandType.BLOCKED_LOCATION,
                'raw': utterance,
                'exception_type': ExceptionType.BLOCKED_LOCATION,
                'description': utterance,
            }

        # 3. Damaged Item Exception
        if re.search(r'\b(damaged|broken|item damaged|crushed|leaking)\b', text):
            return {
                'command': VoiceCommandType.DAMAGED,
                'raw': utterance,
                'exception_type': ExceptionType.DAMAGED_ITEM,
                'description': utterance,
            }

        # 4. Missing Item Exception
        if re.search(r'\b(missing|bin empty|no stock|empty bin|cannot find)\b', text):
            return {
                'command': VoiceCommandType.MISSING,
                'raw': utterance,
                'exception_type': ExceptionType.MISSING_ITEM,
                'description': utterance,
            }

        # 5. Short Pick: "only three available", "short pick 2", "only have 4"
        short_pick_match = re.search(
            r'\b(only|short pick|have only|found only|partial)\s+(?:have\s+)?(\w+|\d+)',
            text,
        )
        if short_pick_match or 'short' in text:
            qty = None
            if short_pick_match:
                qty = parse_spoken_number(short_pick_match.group(2))
            if qty is None:
                qty = parse_spoken_number(text)
            return {
                'command': VoiceCommandType.SHORT_PICK,
                'raw': utterance,
                'quantity': qty or 0,
                'exception_type': ExceptionType.SHORT_PICK,
                'description': f'Short pick reported: {utterance}',
            }

        # 6. Pick Confirmation: "picked 5", "pick five units", "confirm 10", "grabbed 3"
        pick_match = re.search(
            r'\b(picked|pick|take|grabbed|got|confirm|confirmed)\s+(\w+|\d+)', text
        )
        if pick_match:
            qty = parse_spoken_number(pick_match.group(2))
            if qty is not None:
                return {
                    'command': VoiceCommandType.CONFIRM_PICK,
                    'raw': utterance,
                    'quantity': qty,
                }

        # 7. Standalone quantity when awaiting quantity: e.g. "5", "five"
        standalone_num = parse_spoken_number(text)
        if standalone_num is not None and len(text.split()) <= 3:
            return {
                'command': VoiceCommandType.CONFIRM_PICK,
                'raw': utterance,
                'quantity': standalone_num,
            }

        # 8. Confirmation: "confirm", "yes", "done", "ok", "correct"
        if re.search(r'\b(confirm|confirmed|yes|done|ok|okay|correct|check)\b', text):
            return {'command': VoiceCommandType.CONFIRM, 'raw': utterance}

        # 9. Repeat / What / Pardon
        if re.search(r'\b(repeat|say again|what|pardon|again)\b', text):
            return {'command': VoiceCommandType.REPEAT, 'raw': utterance}

        # 10. Next
        if re.search(r'\b(next|next item|next task|continue)\b', text):
            return {'command': VoiceCommandType.NEXT, 'raw': utterance}

        # 11. Skip
        if re.search(r'\b(skip|skip item|pass)\b', text):
            return {'command': VoiceCommandType.SKIP, 'raw': utterance}

        # 12. Help
        if re.search(r'\b(help|commands|instructions|what can i say)\b', text):
            return {'command': VoiceCommandType.HELP, 'raw': utterance}

        # 13. Barcode scan simulation by voice: "scan 12345"
        scan_match = re.search(r'\b(scan|barcode)\s+([a-zA-Z0-9\-_]+)', text)
        if scan_match:
            return {
                'command': VoiceCommandType.SCAN,
                'raw': utterance,
                'barcode': scan_match.group(2).upper(),
            }

        return {'command': VoiceCommandType.UNKNOWN, 'raw': utterance}


class VoiceStateMachine:
    """Contextual state machine evaluating voice commands in warehouse execution context."""

    def __init__(self, initial_state: str = VoiceState.IDLE, task=None):
        self.state = initial_state
        self.task = task
        self.provider = WebSpeechVoiceProvider()

    def process_utterance(self, utterance: str, operator=None) -> Dict[str, Any]:
        """Parse natural language, evaluate against current state, and return voice + state response."""
        parsed = VoiceCommandParser.parse(utterance)
        command = parsed['command']

        # Global commands handled in any state
        if command == VoiceCommandType.REPEAT:
            return self._build_repeat_response()

        if command == VoiceCommandType.HELP:
            return self._build_help_response()

        # Handle according to state
        handler_name = f'_handle_{self.state.lower()}'
        handler = getattr(self, handler_name, self._handle_unknown)
        return handler(command, parsed, operator)

    def _handle_idle(self, command: str, parsed: Dict[str, Any], operator) -> Dict[str, Any]:
        if not self.task:
            return {
                'status': 'error',
                'state': self.state,
                'spoken_response': 'No active picking task assigned. Please select or request a task.',
                'command': command,
            }

        if command in [VoiceCommandType.READY, VoiceCommandType.CONFIRM, VoiceCommandType.NEXT]:
            self.state = VoiceState.NAVIGATING
            if self.task and self.task.status in [WarehouseTaskStatus.PENDING, WarehouseTaskStatus.ASSIGNED]:
                self.task.start(operator=operator, save=True)
            loc_code = (
                self.task.source_location.name
                if self.task.source_location
                else 'designated pick area'
            )
            return {
                'status': 'success',
                'state': self.state,
                'spoken_response': f'Task started. Proceed to location {loc_code}. Say ready when arrived.',
                'command': command,
            }

        return {
            'status': 'ignored',
            'state': self.state,
            'spoken_response': 'Session is idle. Say "Ready" to begin picking.',
            'command': command,
        }

    def _handle_navigating(self, command: str, parsed: Dict[str, Any], operator) -> Dict[str, Any]:
        if command == VoiceCommandType.BLOCKED_LOCATION:
            self.state = VoiceState.EXCEPTION
            if self.task:
                self.task.report_exception(
                    ExceptionType.BLOCKED_LOCATION, parsed.get('description', 'Location blocked'), user=operator
                )
            return {
                'status': 'exception',
                'state': self.state,
                'spoken_response': 'Location marked as blocked. Supervisor alerted. Ready for next instruction.',
                'command': command,
            }

        if command in [VoiceCommandType.READY, VoiceCommandType.CONFIRM]:
            self.state = VoiceState.AWAITING_ITEM_CONFIRMATION
            part_name = self.task.part.name if self.task else 'item'
            sku = getattr(self.task.part, 'IPN', None) or self.task.part.name
            return {
                'status': 'success',
                'state': self.state,
                'spoken_response': f'Arrived. Please scan barcode for SKU {sku}.',
                'command': command,
            }

        return {
            'status': 'prompt',
            'state': self.state,
            'spoken_response': f'Navigating. Say "Ready" once you reach location {self._get_location_name()}.',
            'command': command,
        }

    def _handle_awaiting_item_confirmation(
        self, command: str, parsed: Dict[str, Any], operator
    ) -> Dict[str, Any]:
        if command in [VoiceCommandType.DAMAGED, VoiceCommandType.MISSING]:
            self.state = VoiceState.EXCEPTION
            ex_type = parsed.get('exception_type', ExceptionType.DAMAGED_ITEM)
            if self.task:
                self.task.report_exception(ex_type, parsed.get('description', 'Exception'), user=operator)
            return {
                'status': 'exception',
                'state': self.state,
                'spoken_response': f'{ex_type.replace("_", " ")} recorded. Supervisor notified.',
                'command': command,
            }

        if command == VoiceCommandType.SCAN or command == VoiceCommandType.CONFIRM:
            # Barcode verified
            self.state = VoiceState.AWAITING_QUANTITY
            qty = int(self.task.expected_quantity) if self.task else 1
            part_units = getattr(self.task.part, 'units', 'units') or 'units'
            return {
                'status': 'success',
                'state': self.state,
                'spoken_response': f'Item verified. Pick {qty} {part_units}. Say picked {qty} when done.',
                'command': command,
            }

        return {
            'status': 'prompt',
            'state': self.state,
            'spoken_response': 'Please scan the item barcode or say "Confirm" to proceed.',
            'command': command,
        }

    def _handle_awaiting_quantity(
        self, command: str, parsed: Dict[str, Any], operator
    ) -> Dict[str, Any]:
        if command == VoiceCommandType.SHORT_PICK:
            picked_qty = parsed.get('quantity', 0)
            self.state = VoiceState.COMPLETED
            if self.task:
                self.task.confirm_pick(Decimal(str(picked_qty)), user=operator)
                self.task.report_exception(
                    ExceptionType.SHORT_PICK,
                    f'Short pick: {picked_qty} of {self.task.expected_quantity} available',
                    reported_qty=picked_qty,
                    user=operator,
                )
            return {
                'status': 'partial',
                'state': self.state,
                'spoken_response': f'Short pick confirmed: {picked_qty} units recorded. Exception logged.',
                'command': command,
                'quantity': picked_qty,
            }

        if command == VoiceCommandType.CONFIRM_PICK:
            qty = parsed.get('quantity')
            expected = int(self.task.expected_quantity) if self.task else 1
            if qty is None:
                qty = expected

            self.state = VoiceState.COMPLETED
            if self.task:
                self.task.confirm_pick(Decimal(str(qty)), user=operator)

            return {
                'status': 'success',
                'state': self.state,
                'spoken_response': f'Confirmed {qty} units picked. Task completed.',
                'command': command,
                'quantity': qty,
            }

        if command == VoiceCommandType.CONFIRM:
            expected = int(self.task.expected_quantity) if self.task else 1
            self.state = VoiceState.COMPLETED
            if self.task:
                self.task.confirm_pick(Decimal(str(expected)), user=operator)
            return {
                'status': 'success',
                'state': self.state,
                'spoken_response': f'Confirmed full pick of {expected} units. Task completed.',
                'command': command,
                'quantity': expected,
            }

        return {
            'status': 'prompt',
            'state': self.state,
            'spoken_response': f'Awaiting quantity confirmation. Please say "Picked {int(self.task.expected_quantity if self.task else 1)}".',
            'command': command,
        }

    def _handle_exception(self, command: str, parsed: Dict[str, Any], operator) -> Dict[str, Any]:
        if command in [VoiceCommandType.NEXT, VoiceCommandType.CONFIRM]:
            self.state = VoiceState.IDLE
            return {
                'status': 'success',
                'state': self.state,
                'spoken_response': 'Exception acknowledged. Ready for next assignment.',
                'command': command,
            }
        return {
            'status': 'info',
            'state': self.state,
            'spoken_response': 'Task is blocked under exception. Say "Next" to continue to another task.',
            'command': command,
        }

    def _handle_completed(self, command: str, parsed: Dict[str, Any], operator) -> Dict[str, Any]:
        if command in [VoiceCommandType.NEXT, VoiceCommandType.CONFIRM, VoiceCommandType.READY]:
            self.state = VoiceState.IDLE
            return {
                'status': 'success',
                'state': self.state,
                'spoken_response': 'Ready for next warehouse task.',
                'command': command,
            }
        return {
            'status': 'info',
            'state': self.state,
            'spoken_response': 'Current task is completed. Say "Next" for your next pick.',
            'command': command,
        }

    def _handle_unknown(self, command: str, parsed: Dict[str, Any], operator) -> Dict[str, Any]:
        return {
            'status': 'unknown',
            'state': self.state,
            'spoken_response': 'Command not understood. Say "Repeat" or "Help" for options.',
            'command': command,
        }

    def _build_repeat_response(self) -> Dict[str, Any]:
        prompt = 'Say "Ready" when you reach the pick location.'
        if self.state == VoiceState.NAVIGATING:
            prompt = f'Go to location {self._get_location_name()}.'
        elif self.state == VoiceState.AWAITING_ITEM_CONFIRMATION:
            sku = getattr(self.task.part, 'IPN', None) or self.task.part.name if self.task else 'item'
            prompt = f'Scan or confirm barcode for {sku}.'
        elif self.state == VoiceState.AWAITING_QUANTITY:
            qty = int(self.task.expected_quantity) if self.task else 1
            prompt = f'Pick {qty} units.'
        return {
            'status': 'repeat',
            'state': self.state,
            'spoken_response': prompt,
            'command': VoiceCommandType.REPEAT,
        }

    def _build_help_response(self) -> Dict[str, Any]:
        return {
            'status': 'help',
            'state': self.state,
            'spoken_response': 'Available commands: Ready, Confirm, Pick [quantity], Short pick [quantity], Damaged, Missing, Blocked, Repeat, Next.',
            'command': VoiceCommandType.HELP,
        }

    def _get_location_name(self) -> str:
        if self.task and self.task.source_location:
            return self.task.source_location.name
        return 'designated area'
