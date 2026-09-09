# TDR 003: Voice-Directed Picking Engine & Contextual FSM

## Status
Accepted

## Context
Hands-free voice-directed picking significantly speeds up order fulfillment and reduces picking errors because operators keep both hands free to handle items and scan barcodes. However, voice input in noisy warehouse environments suffers from acoustic interference, misheard utterances, and illegal out-of-turn commands.

## Decision
We implemented a multi-layered voice architecture:
1. **Provider Abstraction (`BaseVoiceProvider`)**:
   - Decouples speech processing from specific vendors.
   - Frontend implementation utilizes standard browser `webkitSpeechRecognition` and `SpeechSynthesisUtterance`.
   - Backend architecture supports offline edge STT engines (such as Vosk or Whisper.cpp) via the same interface.
2. **Intent Parser (`VoiceCommandParser`)**:
   - Normalizes incoming speech and extracts structured commands (`READY`, `CONFIRM`, `CONFIRM_PICK`, `SHORT_PICK`, `DAMAGED`, `REPEAT`, `HELP`, `SCAN`).
   - Supports natural quantity extraction (e.g. "picked twelve" -> `quantity: 12`).
3. **Contextual State Machine (`VoiceStateMachine`)**:
   - Eliminates unexpected side-effects by only permitting valid actions within the current workflow state:
     - `IDLE` -> only responds to "Ready" or "Start".
     - `NAVIGATING` -> responds to "Arrived" or "Blocked".
     - `AWAITING_ITEM_CONFIRMATION` -> requires SKU scan or "Confirm".
     - `AWAITING_QUANTITY` -> accepts "Picked <N>", "Confirm", or "Short Pick".
   - Out-of-turn or unrecognized utterances prompt clarification rather than executing erroneous state changes.

## Consequences
- **Positive**: Hands-free picking is robust against out-of-order spoken commands.
- **Positive**: Fully testable through automated unit and integration tests without physical microphone hardware.
