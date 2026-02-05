"""
Retrace Provenance Integration Module

Combines retracesoftware.proxy (replay) with retrace-interpreter (provenance).

Usage:
    python retrace_provenance.py --recording <path> [--step <N>]

This module:
1. Loads a recording (trace.bin) created with the new proxy (v0.2.20)
2. Sets up replay mode (external calls return recorded results)
3. Runs through the retrace-interpreter for provenance tracking

Integration Note:
    The interpreter is run with use_subinterpreter=False to keep proxy patches
    active in the current interpreter. This allows external calls to be replayed
    from the recording while provenance is being tracked.
"""

import sys
import os
import argparse
import json
import gc
from pathlib import Path

# Add retrace-interpreter to path
INTERPRETER_PATH = Path(__file__).parent / 'retrace-interpreter'
if INTERPRETER_PATH.exists() and str(INTERPRETER_PATH) not in sys.path:
    sys.path.insert(0, str(INTERPRETER_PATH))

# New proxy imports
import retracesoftware.utils as utils
import retracesoftware.stream as stream
from retracesoftware.proxy.replay import ReplayProxySystem
from retracesoftware.proxy.startthread import thread_id
from retracesoftware.run import install, run_python_command, run_with_retrace, ImmutableTypes, thread_states


def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_env(file):
    """Load a .env file into a dict."""
    env = {}
    with open(file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                value = value.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                env[key] = value
    return env


class ProvenanceSession:
    """
    Manages a provenance analysis session.

    Combines replay (from trace.bin) with the interpreter (for provenance tracking).
    """

    def __init__(self, recording_path: Path, verbose: bool = False):
        self.recording_path = Path(recording_path).resolve()
        self.verbose = verbose
        self.settings = None
        self.system = None
        self.reader = None

    def load(self):
        """Load recording metadata and validate."""
        if not self.recording_path.exists():
            raise FileNotFoundError(f"Recording path: {self.recording_path} does not exist")

        self.settings = load_json(self.recording_path / "settings.json")

        if self.settings['python_version'] != sys.version:
            print(f"Warning: Python version mismatch", file=sys.stderr)
            print(f"  Recorded: {self.settings['python_version']}", file=sys.stderr)
            print(f"  Current:  {sys.version}", file=sys.stderr)

        return self

    def setup_replay(self, read_timeout: int = 1000, skip_weakref_callbacks: bool = True):
        """
        Set up the replay proxy system.

        After calling this, external calls will return recorded results.
        """
        # Load environment from recording
        os.environ.update(load_env(self.recording_path / '.env'))

        # Change to recorded cwd
        os.chdir(self.settings['cwd'])

        # Create thread state
        thread_state = utils.ThreadState(*thread_states)

        # Open trace reader
        self.reader = stream.reader1(
            path=self.recording_path / 'trace.bin',
            read_timeout=read_timeout,
            verbose=self.verbose,
            magic_markers=self.settings.get('magic_markers', False)
        )
        self.reader.__enter__()

        # Create replay proxy system
        self.system = ReplayProxySystem(
            reader=self.reader,
            thread_state=thread_state,
            immutable_types=ImmutableTypes(),
            tracing_config={},
            traceargs=self.settings.get('trace_inputs', False),
            verbose=self.verbose,
            skip_weakref_callbacks=skip_weakref_callbacks
        )

        # Install patches
        install(self.system)

        gc.collect()
        gc.disable()

        return self

    def run_replay_only(self):
        """
        Run replay without provenance tracking.

        This is equivalent to `python -m retracesoftware --recording <path>`.
        """
        if not self.system:
            raise RuntimeError("Call setup_replay() first")

        run_with_retrace(self.system, self.settings['argv'], self.settings.get('trace_shutdown', False))

    def run_with_provenance(self, callback=None):
        """
        Run replay with provenance tracking through the interpreter.

        Args:
            callback: Function called at instruction boundaries.
                      Receives ThreadState with .counter, .frame_counter, .thread
                      Return an int to schedule next callback at that instruction count.
                      Return None to disable callbacks.

        NOTE: This requires retrace-interpreter to be installed and
              properly integrated with the proxy system.
        """
        if not self.system:
            raise RuntimeError("Call setup_replay() first")

        try:
            import retraceinterpreter
        except ImportError:
            raise ImportError(
                "retrace-interpreter not installed. "
                "Build and install from the retrace-interpreter repository."
            )

        def target():
            # Use run_with_retrace instead of run_python_command
            # This sets up the thread state properly for proxy interception
            run_with_retrace(self.system, self.settings['argv'], self.settings.get('trace_shutdown', False))

        def default_callback(state):
            if self.verbose:
                print(f"Step {state.counter}: frame_counter={state.frame_counter}")
            return state.counter + 1000  # Print every 1000 instructions

        # Run through the interpreter
        # Using use_subinterpreter=False to keep proxy patches active
        return retraceinterpreter.run(
            target=target,
            args=(),
            kwargs={},
            callback=callback or default_callback,
            use_subinterpreter=False  # Keep proxy patches in current interpreter
        )

    def cleanup(self):
        """Clean up resources."""
        if self.reader:
            self.reader.__exit__(None, None, None)
            self.reader = None

    def __enter__(self):
        return self.load()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False


def example_callback(state):
    """
    Example callback for provenance analysis.

    Called at instruction boundaries during interpreter execution.
    """
    print(f"Instruction {state.counter}")
    print(f"  Frame started at: {state.frame_counter}")
    print(f"  Thread: {state.thread}")

    # Return next instruction count to pause at, or None to continue to end
    # return state.counter + 1000  # Pause every 1000 instructions
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Run provenance analysis on a Retrace recording"
    )

    parser.add_argument(
        '--recording', '-r',
        type=str,
        required=True,
        help='Path to the recording directory'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--replay-only',
        action='store_true',
        help='Run replay without provenance tracking'
    )

    parser.add_argument(
        '--step',
        type=int,
        default=None,
        help='Stop at specific instruction count'
    )

    args = parser.parse_args()

    with ProvenanceSession(args.recording, verbose=args.verbose) as session:
        session.setup_replay()

        if args.replay_only:
            print("Running replay (no provenance)...")
            session.run_replay_only()
        else:
            print("Running with provenance tracking...")

            if args.step:
                def stop_at_step(state):
                    if state.counter >= args.step:
                        print(f"\nStopped at instruction {state.counter}")
                        print(f"Frame counter: {state.frame_counter}")
                        return None  # Stop
                    return args.step  # Continue to target

                session.run_with_provenance(callback=stop_at_step)
            else:
                session.run_with_provenance(callback=example_callback)


if __name__ == "__main__":
    main()
