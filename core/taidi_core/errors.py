"""Errors raised by the state machine. The future API maps these to HTTP status codes."""


class MachineError(Exception):
    """Base class for every rejection the state machine can raise."""


class IllegalTransition(MachineError):
    """The command doesn't make sense in the room's current state."""


class NotAuthorized(MachineError):
    """The actor isn't allowed to issue this command."""


class SeqConflict(MachineError):
    """The caller's expected_seq is stale — someone else's event landed first."""

    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        super().__init__(f"expected_seq={expected} but room is at seq={actual}")
