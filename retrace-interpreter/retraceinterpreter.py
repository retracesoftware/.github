"""
Retrace Interpreter Python wrapper module.

Provides a high-level API for the _retraceinterpreter C extension.
Includes provenance tracking for debugging "where did this value come from?"
"""

import sys
import os
import dis
import opcode

# Add this directory to path to find the C extension
_module_dir = os.path.dirname(os.path.abspath(__file__))
if _module_dir not in sys.path:
    sys.path.insert(0, _module_dir)

import _retraceinterpreter


def _default_thread_id(modules):
    """Default thread ID function."""
    import threading
    return threading.current_thread().ident


class ProvenanceInfo:
    """Information about when/where a value was created or modified."""

    def __init__(self, instruction_counter, frame_id, variable_name, filename, lineno, opname):
        self.instruction_counter = instruction_counter
        self.frame_id = frame_id
        self.variable_name = variable_name
        self.filename = filename
        self.lineno = lineno
        self.opname = opname
        self.sources = []  # For tracking data flow (which values this came from)

    def __repr__(self):
        return (f"ProvenanceInfo(instr={self.instruction_counter}, "
                f"var={self.variable_name!r}, line={self.lineno}, op={self.opname})")


class ProvenanceTracker:
    """
    Tracks provenance of values during execution.

    Monitors variable assignments and tracks which instruction created each value.
    """

    def __init__(self):
        # Map: (frame_id, var_name) -> ProvenanceInfo
        self.variable_provenance = {}

        # Map: frame_id -> list of ProvenanceInfo (stack simulation)
        self.stack_provenance = {}

        # History of all provenance events
        self.history = []

        # Current state
        self.instruction_counter = 0
        self.frame_counter = 0

        # Opcodes that store values
        self.store_opcodes = {
            'STORE_FAST', 'STORE_NAME', 'STORE_GLOBAL', 'STORE_DEREF',
            'STORE_ATTR', 'STORE_SUBSCR'
        }

        # Opcodes that load values (push to stack)
        self.load_opcodes = {
            'LOAD_FAST', 'LOAD_NAME', 'LOAD_GLOBAL', 'LOAD_DEREF',
            'LOAD_CONST', 'LOAD_ATTR'
        }

        # Binary operations (pop 2, push 1)
        self.binary_opcodes = {
            'BINARY_ADD', 'BINARY_SUBTRACT', 'BINARY_MULTIPLY', 'BINARY_TRUE_DIVIDE',
            'BINARY_FLOOR_DIVIDE', 'BINARY_MODULO', 'BINARY_POWER',
            'BINARY_AND', 'BINARY_OR', 'BINARY_XOR',
            'BINARY_LSHIFT', 'BINARY_RSHIFT',
            'BINARY_SUBSCR', 'BINARY_OP'
        }

    def trace(self, frame, event, arg):
        """Trace function for provenance tracking."""
        if event == 'opcode':
            self.instruction_counter += 1
            self._track_opcode(frame)
        elif event == 'call':
            self.frame_counter += 1
            frame.f_trace_opcodes = True
            # Initialize stack for this frame
            frame_id = id(frame)
            if frame_id not in self.stack_provenance:
                self.stack_provenance[frame_id] = []
        elif event == 'return':
            # Clean up frame stack
            frame_id = id(frame)
            if frame_id in self.stack_provenance:
                del self.stack_provenance[frame_id]

        return self.trace

    def _track_opcode(self, frame):
        """Track a single opcode execution."""
        code = frame.f_code
        # In Python 3.11+, use f_lasti to get instruction offset
        offset = frame.f_lasti

        # Get the instruction at this offset
        try:
            instructions = list(dis.get_instructions(code))
            # Find instruction by offset
            instr = None
            for i in instructions:
                if i.offset == offset:
                    instr = i
                    break

            if instr is None:
                return

            opname = instr.opname
            arg = instr.arg
            argval = instr.argval

            frame_id = id(frame)

            # Track store operations
            if opname in self.store_opcodes:
                var_name = argval if argval else f"arg_{arg}"
                prov = ProvenanceInfo(
                    instruction_counter=self.instruction_counter,
                    frame_id=frame_id,
                    variable_name=var_name,
                    filename=code.co_filename,
                    lineno=frame.f_lineno,
                    opname=opname
                )

                # If we have stack provenance, record where the value came from
                stack = self.stack_provenance.get(frame_id, [])
                if stack:
                    prov.sources = [stack.pop()]

                self.variable_provenance[(frame_id, var_name)] = prov
                self.history.append(prov)

            # Track load operations (push provenance to stack)
            elif opname in self.load_opcodes:
                stack = self.stack_provenance.setdefault(frame_id, [])
                var_name = argval if argval else f"arg_{arg}"

                if opname == 'LOAD_CONST':
                    # Constants have provenance at their load point
                    prov = ProvenanceInfo(
                        instruction_counter=self.instruction_counter,
                        frame_id=frame_id,
                        variable_name=f"const:{argval!r}",
                        filename=code.co_filename,
                        lineno=frame.f_lineno,
                        opname=opname
                    )
                else:
                    # Look up variable provenance
                    prov = self.variable_provenance.get((frame_id, var_name))
                    if prov is None:
                        # Variable not tracked yet (e.g., function argument)
                        prov = ProvenanceInfo(
                            instruction_counter=self.instruction_counter,
                            frame_id=frame_id,
                            variable_name=var_name,
                            filename=code.co_filename,
                            lineno=frame.f_lineno,
                            opname=opname
                        )

                stack.append(prov)

            # Track binary operations (combine provenance)
            elif opname in self.binary_opcodes:
                stack = self.stack_provenance.setdefault(frame_id, [])
                sources = []
                if len(stack) >= 2:
                    sources = [stack.pop(), stack.pop()]

                # Create new provenance for the result
                prov = ProvenanceInfo(
                    instruction_counter=self.instruction_counter,
                    frame_id=frame_id,
                    variable_name=f"<{opname}>",
                    filename=code.co_filename,
                    lineno=frame.f_lineno,
                    opname=opname
                )
                prov.sources = sources
                stack.append(prov)
                self.history.append(prov)

        except Exception:
            # Don't let tracking errors break execution
            pass

    def get_variable_provenance(self, frame, var_name):
        """Get provenance info for a variable in a frame."""
        frame_id = id(frame)
        return self.variable_provenance.get((frame_id, var_name))

    def get_all_provenance(self):
        """Get all tracked provenance information."""
        return dict(self.variable_provenance)

    def get_history(self):
        """Get chronological history of provenance events."""
        return list(self.history)

    def trace_value_origin(self, prov, depth=0, max_depth=10):
        """
        Trace the origin of a value recursively.

        Returns a tree of provenance showing where the value came from.
        """
        if prov is None or depth > max_depth:
            return None

        result = {
            'instruction': prov.instruction_counter,
            'variable': prov.variable_name,
            'line': prov.lineno,
            'operation': prov.opname,
            'sources': []
        }

        for source in prov.sources:
            source_trace = self.trace_value_origin(source, depth + 1, max_depth)
            if source_trace:
                result['sources'].append(source_trace)

        return result


class InstructionCounter:
    """Counts instructions and triggers callbacks at specified points."""

    def __init__(self, callback, callback_at=1, provenance_tracker=None):
        self.callback = callback
        self.callback_at = callback_at
        self.counter = 0
        self.frame_counter = 0
        self.provenance_tracker = provenance_tracker

    def trace(self, frame, event, arg):
        """Trace function called for each event."""
        # First, let provenance tracker process the event
        if self.provenance_tracker:
            self.provenance_tracker.trace(frame, event, arg)
            # Sync counters
            self.counter = self.provenance_tracker.instruction_counter
            self.frame_counter = self.provenance_tracker.frame_counter

        if event == 'opcode':
            if not self.provenance_tracker:
                self.counter += 1

            if self.callback_at > 0 and self.counter >= self.callback_at:
                # Create a state object for the callback
                state = type('ThreadState', (), {
                    'counter': self.counter,
                    'frame_counter': self.frame_counter,
                    'callback_counter': self.callback_at,
                    'thread': None,
                    'frame': frame,
                    'provenance': self.provenance_tracker
                })()
                result = self.callback(state)
                if result is None:
                    self.callback_at = 0  # Disable further callbacks
                elif isinstance(result, int):
                    self.callback_at = result

        elif event == 'call':
            if not self.provenance_tracker:
                self.frame_counter += 1
            frame.f_trace_opcodes = True

        return self.trace


def run(target, args=(), kwargs=None, callback=None, use_subinterpreter=True,
        callback_at=1, track_provenance=False):
    """
    Run a target function through the retrace interpreter.

    Args:
        target: The callable to execute
        args: Positional arguments for the target (default: ())
        kwargs: Keyword arguments for the target (default: {})
        callback: Function called at instruction boundaries.
                  Receives a ThreadState object with attributes:
                    - counter: Current instruction count
                    - frame_counter: Number of frames created
                    - callback_counter: Next callback trigger point
                    - thread: Thread object
                    - frame: Current frame (if provenance tracking enabled)
                    - provenance: ProvenanceTracker instance (if enabled)
                  Return an int to schedule next callback at that instruction count.
                  Return None to disable further callbacks.
        use_subinterpreter: If True (default), run in a sub-interpreter.
                           If False, run in the current interpreter (keeps proxy patches).
        callback_at: Instruction count to trigger first callback (default: 1).
                    Set to 0 to disable callbacks entirely.
        track_provenance: If True, track provenance of values (default: False).

    Returns:
        The return value of the target function.
        If track_provenance=True, returns (result, ProvenanceTracker).

    Example:
        def my_callback(state):
            print(f"At instruction {state.counter}")
            if state.provenance:
                # Access provenance information
                for (fid, var), prov in state.provenance.get_all_provenance().items():
                    print(f"  {var}: created at instruction {prov.instruction_counter}")
            return state.counter + 100

        result, tracker = run(my_function, callback=my_callback, track_provenance=True)
    """
    if kwargs is None:
        kwargs = {}

    def _default_callback(state):
        return None  # Disable callbacks by default

    provenance_tracker = ProvenanceTracker() if track_provenance else None

    # If we have a callback or want provenance tracking, use Python tracing
    # For provenance, we need tracing even if callback_at=0
    needs_tracing = ((callback and callback_at > 0) or track_provenance) and not use_subinterpreter
    if needs_tracing:
        # Use callback_at=1 for provenance if not specified, to enable tracing
        effective_callback_at = callback_at if callback_at > 0 else (1 if track_provenance else 0)
        counter = InstructionCounter(
            callback or _default_callback,
            effective_callback_at if callback else 0,  # Disable callback triggers if no callback
            provenance_tracker
        )
        old_trace = sys.gettrace()

        def wrapper():
            # Set trace before calling target
            sys.settrace(counter.trace)
            try:
                return target(*args, **(kwargs or {}))
            finally:
                sys.settrace(old_trace)

        # Run through the C interpreter (for frame evaluation override)
        # but use Python tracing for instruction counting
        result = _retraceinterpreter.run(
            target=wrapper,
            args=(),
            kwargs={},
            main_thread=_default_thread_id,
            thread=_default_thread_id,
            callback=_default_callback,  # Callbacks handled by Python tracer
            use_subinterpreter=False,
            callback_at=0  # Disable C-level callbacks
        )

        if track_provenance:
            return result, provenance_tracker
        return result
    else:
        # Use C-level callback mechanism
        result = _retraceinterpreter.run(
            target=target,
            args=args,
            kwargs=kwargs,
            main_thread=_default_thread_id,
            thread=_default_thread_id,
            callback=callback or _default_callback,
            use_subinterpreter=use_subinterpreter,
            callback_at=callback_at
        )

        if track_provenance:
            return result, provenance_tracker
        return result


__all__ = ['run', 'ProvenanceTracker', 'ProvenanceInfo']
